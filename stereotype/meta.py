from __future__ import annotations

from typing import Dict, Any, Iterable, Tuple, get_type_hints, cast, List, Set, Type, TYPE_CHECKING, Optional, \
    get_origin, ClassVar

from stereotype.fields.annotations import AnnotationResolver
from stereotype.fields.base import Field
from stereotype.fields.serializable import SerializableField
from stereotype.roles import Role, RequestedRoleFields, FinalizedRoleFields, _AbstractMemberDescriptor
from stereotype.utils import ConfigurationError, Missing

if TYPE_CHECKING:  # pragma: no cover
    from stereotype.model import Model


class ModelMeta(type):
    def __new__(mcs, name: str, bases: Tuple[type, ...], attrs: Dict[str, Any]):
        if not bases:
            return type.__new__(mcs, name, bases, attrs)

        # Only annotated attributes iterated here for the purposes of slots, not serializable fields
        field_names = list(mcs._iterate_own_fields(attrs.get('__annotations__', {})))
        mcs._check_explicit_field_annotations(name, set(field_names), attrs)
        field_values = {}
        for field_name in field_names:
            if field_name in attrs:
                # Field attributes popped as they will become instance attributes instead of class attributes
                field_values[field_name] = attrs.pop(field_name)

        # Find serializable, keep them in `attrs` as they need to remain as properties
        serializable_names = {name for name, _ in mcs._iterate_serializable(attrs)}
        own_field_names = set(field_names) | serializable_names

        # Using dicts instead of sets to preserve order
        attrs['__abstract_slots__'] = all_slots = [slot for slot in {
            **{slot: 0 for slot in mcs._iterate_base_fields(bases)},
            **{slot: 1 for slot in field_names},
            **{slot: 2 for slot in attrs.get('__slots__', ())},
        } if slot not in serializable_names]

        if attrs.get('__abstract__', False):
            attrs.pop('__slots__', None)
            # Without slots there will be no native member_descriptors (needed for declaring roles), supply fake ones
            attrs.update({field_name: _AbstractMemberDescriptor(field_name) for field_name in field_names})
        else:
            attrs['__slots__'] = all_slots

        attrs['__fields__'] = NotImplemented
        attrs['__input_fields__'] = NotImplemented
        attrs['__validated_fields__'] = NotImplemented
        attrs['__role_fields__'] = NotImplemented
        attrs['__roles__'] = NotImplemented
        attrs['__gettable__'] = set(all_slots) | set(mcs._iterate_base_gettable(bases)) | mcs._find_properties(attrs)

        try:
            cls = cast(Type['Model'], type.__new__(mcs, name, bases, attrs))
        except TypeError as e:
            raise ConfigurationError(f'{name}: {e}, if inheriting from multiple models, only one may have __slots__ '
                                     f'(declare abstract models without __slots__ by adding class attribute '
                                     f'`__abstract__ = True`)')
        cls.__initialize_model__ = lambda *_: mcs._initialize_model(cls, bases, own_field_names, field_values)
        return cls

    @classmethod
    def _iterate_own_fields(mcs, field_annotations: Dict[str, Any]) -> Iterable[str]:
        for name, annotation in field_annotations.items():
            if name.startswith('_'):
                continue  # Private attributes won't become fields
            # Skip attributes with ClassVar annotations - they shouldn't become fields
            if isinstance(annotation, str):
                # Delayed annotation; it's not a good time to resolve type hints properly, work with it as a string
                class_var_prefix = annotation.startswith('ClassVar[') or annotation.startswith('typing.ClassVar[')
                if class_var_prefix and annotation.endswith(']'):
                    continue
            elif get_origin(annotation) is ClassVar:
                continue
            yield name

    @classmethod
    def _iterate_base_fields(mcs, bases: Tuple[type, ...]) -> Iterable[str]:
        from stereotype.model import Model
        for base in bases:
            if not issubclass(base, Model):
                continue
            yield from getattr(base, '__abstract_slots__', ())

    @classmethod
    def _check_explicit_field_annotations(mcs, cls_name: str, field_names: Set[str], attrs: Dict[str, Any]):
        for name, value in attrs.items():
            if isinstance(value, Field) and name not in field_names:
                raise ConfigurationError(f"Field {name} of Model class {cls_name} defines an explicit Field "
                                         f"but lacks a type annotation or isn't public")

    @classmethod
    def _initialize_model(mcs, cls: Type[Model], bases: Tuple[type, ...],
                          own_field_names: Set[str], field_values: dict):
        from stereotype.model import Model
        model_bases = [base for base in bases if issubclass(base, Model) and base is not Model]
        mcs._ensure_parent_models(model_bases, own_field_names, field_values)

        serializable = list(mcs._analyze_serializable(cls))
        serializable_names = {field.name for field in serializable}
        input_fields = [field for field in mcs._analyze_fields(cls, field_values)
                        if field.name not in serializable_names]
        cls.__input_fields__ = [field.make_input_config() for field in input_fields]
        cls.__validated_fields__ = [field.make_validated_config() for field in input_fields if field.has_validation()]
        cls.__fields__ = input_fields + serializable
        mcs._build_roles(cls, model_bases, own_field_names)

    @classmethod
    def _ensure_parent_models(mcs, model_bases: List[Type[Model]], own_field_names: Set[str], field_values: dict):
        for base in model_bases:
            if base.__fields__ is NotImplemented:
                base.__initialize_model__()
            for field in base.__fields__:
                if field.name not in own_field_names:
                    field_values[field.name] = field

    @classmethod
    def _analyze_fields(mcs, cls: Type[Model], field_values: dict) -> Iterable[Field]:
        all_field_names = set(getattr(cls, '__abstract_slots__', ()))
        for name, annotation in mcs._resolve_annotations(cls).items():
            if name not in all_field_names:
                continue

            explicit_field: Optional[Field] = None
            default = Missing
            if name in field_values:
                value = field_values[name]
                if isinstance(value, Field):
                    explicit_field = value
                else:
                    default = value

            try:
                field = AnnotationResolver(annotation).resolve(explict_field=explicit_field)
                field.init_name(name)
                if default is not Missing:
                    field.init_default(default)
                # Note a default could have also been present in the explicit field
                field.check_default()
            except ConfigurationError as e:
                raise ConfigurationError(f"Field {name} of {cls.__name__}: {e}")

            validator_method = getattr(cls, f'validate_{name}', None)
            if validator_method is not None:
                field.validator_method = validator_method

            yield field

    @classmethod
    def _iterate_serializable(mcs, attrs: Dict[str, Any]) -> Iterable[Tuple[str, SerializableField]]:
        for name, attr in attrs.items():
            if not isinstance(attr, property) or not hasattr(attr.fget, '__field__'):
                continue
            field = getattr(attr.fget, '__field__')
            if isinstance(field, SerializableField):
                yield name, field

    @classmethod
    def _analyze_serializable(mcs, cls: Type[Model]):
        attrs = {name: getattr(cls, name) for name in dir(cls)}
        for name, field in mcs._iterate_serializable(attrs):
            field.init_name(name)
            yield field

    @classmethod
    def _find_properties(mcs, attrs: Dict[str, Any]) -> Set[str]:
        """Enumerates properties and serializable fields (as they are also properties) of the model class."""
        return {name for name, attr in attrs.items() if isinstance(attr, property)}

    @classmethod
    def _iterate_base_gettable(mcs, bases: Tuple[type, ...]) -> Iterable[str]:
        from stereotype.model import Model
        for base in bases:
            if not issubclass(base, Model):
                continue
            yield from getattr(base, '__gettable__', ())

    @staticmethod
    def _resolve_annotations(cls: Type[Model]) -> Dict[str, Any]:
        extra_types: Set[Type[Model]] = cls.resolve_extra_types()
        extra_locals = {typ.__name__: typ for typ in extra_types}
        try:
            return get_type_hints(cls, localns=extra_locals)
        except NameError as e:
            raise ConfigurationError(f'Model {cls.__name__} annotation {str(e)}. If not a global symbol or cannot be '
                                     f'imported globally, use the class method `resolve_extra_types` to provide it.')

    @classmethod
    def _build_roles(mcs, cls: Type[Model], bases: List[Type[Model]], own_field_names: Set[str]):
        roles = mcs._collect_finalized_roles(cls, bases, own_field_names)
        max_role_code = max((role.code for role in roles.keys()), default=0)
        default_role_fields = [
            field.make_output_config() for field in cls.__fields__ if field.to_primitive_name is not None
        ]
        cls.__role_fields__ = [default_role_fields] * (max_role_code + 1)
        cls.__roles__ = []

        for role, finalized in roles.items():
            field_configs = [
                field.make_output_config() for field in cls.__fields__
                if field.name in finalized.fields and field.to_primitive_name is not None
            ]
            cls.__role_fields__[role.code] = field_configs
            cls.__roles__.append(finalized)

    @classmethod
    def _collect_finalized_roles(mcs, cls: Type[Model], bases: List[Type[Model]], own_field_names: Set[str],
                                 ) -> Dict[Role, FinalizedRoleFields]:
        all_field_names, own_requested_roles = mcs._collect_own_requested_roles(cls)
        all_roles = {finalized.role for base in bases for finalized in base.__roles__} | set(own_requested_roles.keys())
        roles: Dict[Role, FinalizedRoleFields] = {role: FinalizedRoleFields(role) for role in all_roles}

        for base in reversed(bases):
            base_roles: Dict[Role, FinalizedRoleFields] = {finalized.role: finalized for finalized in base.__roles__}
            for role, finalized in roles.items():
                base_finalized = base_roles.get(role)
                if base_finalized is not None:
                    finalized.fields.update(base_finalized.fields)
                elif not role.empty_by_default:
                    finalized.fields.update(field.name for field in base.__fields__)

        for role, finalized in roles.items():
            own_requested = own_requested_roles.get(role)
            if own_requested is not None:
                finalized.update_requested(own_requested, all_field_names, own_field_names)
            elif not role.empty_by_default:
                finalized.fields.update(own_field_names)

        return roles

    @classmethod
    def _collect_own_requested_roles(mcs, cls: Type[Model]) -> Tuple[Set[str], Dict[Role, RequestedRoleFields]]:
        all_field_names = {field.name for field in cls.__fields__}
        own_requested_roles: Dict[Role, RequestedRoleFields] = {}
        for requested in cls.declare_roles():
            if requested.role in own_requested_roles:
                raise ConfigurationError(f'Role {requested.role.name} configured for {cls.__name__} multiple times')
            own_requested_roles[requested.role] = requested
        return all_field_names, own_requested_roles
