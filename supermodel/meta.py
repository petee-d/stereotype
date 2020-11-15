from __future__ import annotations

from typing import Dict, Any, Iterable, Tuple, get_type_hints, cast, List, Union, Set, Type, TYPE_CHECKING

from supermodel.fields.base import Field, AnyField
from supermodel.fields.compound import ListField, DictField
from supermodel.fields.serializable import SerializableField
from supermodel.roles import Role, RequestedRoleFields, FinalizedRoleFields
from supermodel.utils import ConfigurationError

if TYPE_CHECKING:  # pragma: no cover
    from supermodel.model import Model


class ModelMeta(type):
    def __new__(mcs, name: str, bases: Tuple[type, ...], attrs: Dict[str, Any]):
        if not bases:
            return type.__new__(mcs, name, bases, attrs)

        # Only annotated attributes iterated here for the purposes of slots, not serializable fields
        field_names = [name for name, annotation in mcs._iterate_fields(attrs.get('__annotations__', {}))]
        field_values = {}
        for field_name in field_names:
            if field_name in attrs:
                # Field attributes popped as they will become instance attributes instead of class attributes
                field_values[field_name] = attrs.pop(field_name)

        # Find serializable, keep them in `attrs` as they need to remain as properties
        serializable_names = {name for name, _ in mcs._iterate_serializable(attrs)}

        # Using dicts instead of sets to preserve order
        all_slots = {
            **{slot: 0 for parent in bases for slot in parent.__slots__ or getattr(parent, '__abstract_slots__', ())},
            **{slot: 1 for slot in field_names},
            **{slot: 2 for slot in attrs.get('__slots__', ())},
        }
        if attrs.pop('__abstract__', False):
            attrs['__abstract_slots__'] = all_slots
        else:
            attrs['__slots__'] = [name for name in all_slots if name not in serializable_names]
        attrs['__fields__'] = NotImplemented
        attrs['__input_fields__'] = NotImplemented
        attrs['__role_fields__'] = NotImplemented
        attrs['__roles__'] = NotImplemented

        own_field_names = set(field_names) | serializable_names

        try:
            cls = cast(Type['Model'], type.__new__(mcs, name, bases, attrs))
        except TypeError as e:
            raise ConfigurationError(f'{name}: {e}, if inheriting from multiple models, only one may have __slots__ '
                                     f'(declare abstract models without __slots__ by adding class attribute '
                                     f'`__abstract__ = True`)')
        cls.__initialize_model__ = lambda *_: mcs._initialize_model(cls, bases, own_field_names, field_values)
        return cls

    @classmethod
    def _iterate_fields(mcs, field_annotations: Dict[str, Any]) -> Iterable[Tuple[str, Any]]:
        for name, annotation in field_annotations.items():
            if name.startswith('_'):
                continue
            yield name, annotation

    @classmethod
    def _initialize_model(mcs, cls: Type[Model], bases: Tuple[type, ...],
                          own_field_names: Set[str], field_values: dict):
        from supermodel.model import Model
        model_bases = [base for base in bases if issubclass(base, Model) and base is not Model]
        mcs._ensure_parent_models(model_bases, own_field_names, field_values)

        serializable = list(mcs._analyze_serializable(cls))
        serializable_names = {field.name for field in serializable}
        input_fields = [field for field in mcs._analyze_fields(cls, field_values)
                        if field.name not in serializable_names]
        cls.__input_fields__ = [field.make_input_config() for field in input_fields]
        cls.__fields__ = input_fields + serializable
        mcs._build_roles(cls, model_bases, own_field_names)

    @classmethod
    def _ensure_parent_models(mcs, model_bases: List[Type[Model]], own_field_names: Set[str], field_values: dict):
        for base in model_bases:
            if base.__fields__ is NotImplemented:
                base.__initialize_model__()
            for field in cast(List[Field], base.__fields__):
                if field.name not in own_field_names:
                    field_values[field.name] = field.copy()

    @classmethod
    def _analyze_fields(mcs, cls: Type[Model], field_values: dict) -> Iterable[Field]:
        for name, annotation in mcs._iterate_fields(mcs._resolve_annotations(cls)):
            analyzed_field = mcs._analyze_annotation(annotation)
            value = field_values.get(name)
            if isinstance(value, Field):
                field = value
                if not isinstance(field, type(analyzed_field)):
                    field.fill_in_name(name)
                    analyzed_field.fill_in_name(name)
                    raise ConfigurationError(f'Annotations for {analyzed_field} require custom field type '
                                             f'{type(analyzed_field).__name__}, got {type(field).__name__}')
                field.type_config_from(analyzed_field)
            else:
                field = analyzed_field
                if name in field_values:
                    field.set_default(value)

            field.fill_in_name(name)
            field.check_default()

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
            field.fill_in_name(name)
            yield field

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
    def _analyze_annotation(mcs, annotation) -> Field:
        """Any supported annotation -> any Field"""
        from supermodel.model import Model

        typing_repr = repr(annotation)
        if typing_repr.startswith('typing.'):
            if typing_repr.startswith('typing.List['):
                return mcs._analyze_annotation_list(annotation)
            if typing_repr.startswith('typing.Dict['):
                return mcs._analyze_annotation_dict(annotation)
            if typing_repr.startswith('typing.Union['):
                return mcs._analyze_annotation_union(annotation)
            if typing_repr == 'typing.Any':
                return AnyField()
        else:
            if annotation in (bool, int, float, str):
                return mcs._analyze_annotation_atomic(annotation)
            if issubclass(annotation, Model):
                return mcs._analyze_annotation_model(annotation)

        raise ConfigurationError(f'Unsupported Model field {annotation!r}')

    @classmethod
    def _analyze_annotation_atomic(mcs, annotation) -> Field:
        """Atomic types -> atomic Field"""
        from supermodel.fields.atomic import ATOMIC_TYPE_MAPPING
        return ATOMIC_TYPE_MAPPING[annotation]()

    @classmethod
    def _analyze_annotation_model(mcs, annotation) -> Field:
        """Model subclass -> ModelField"""
        from supermodel import ModelField
        field = ModelField()
        field.type = annotation
        return field

    @classmethod
    def _analyze_annotation_union(mcs, annotation) -> Field:
        """Optional or Union -> any Field with allow_none or DynamicModelField"""
        from supermodel.model import Model

        options = annotation.__args__
        non_none = [option for option in options if option not in (type(None),)]

        if len(non_none) < len(options):
            # Optional is always represented by Union[None, ...]
            return mcs._analyze_annotation_optional(non_none)
        elif all(issubclass(option, Model) for option in options):
            return mcs._analyze_annotation_model_union(annotation, options)
        else:
            raise ConfigurationError(f'Union Model fields can only be Optional or Union of Model subclass types, '
                                     f'got {annotation!r}')

    @classmethod
    def _analyze_annotation_optional(mcs, non_none: List[Any]) -> Field:
        """Optional[...] -> any Field with allow_none"""
        optional_type = non_none[0] if len(non_none) == 1 else Union[tuple(non_none)]
        field = mcs._analyze_annotation(optional_type)
        field.allow_none = True
        return field

    @classmethod
    def _analyze_annotation_model_union(mcs, annotation, options: List[Any]) -> Field:
        """Union[ModelSubClass, ...] -> DynamicModelField"""
        from supermodel import DynamicModelField

        type_map = {}
        for option in options:
            if not hasattr(option, 'type'):
                raise ConfigurationError(f"Model {option.__name__} used in a dynamic model field {annotation} but does "
                                         f"not define a non-type-annotated string `type` field")
            if type(option.type).__name__ == 'member_descriptor':
                raise ConfigurationError(f"Model {option.__name__} used in a dynamic model field {annotation} but it's "
                                         f"`type` field has a type annotation making it a field, must be an attribute")
            if not isinstance(option.type, str):
                raise ConfigurationError(f"Model {option.__name__} used in a dynamic model field {annotation} but it's "
                                         f"`type` field {option.type} is not a string")
            if option.type in type_map:
                raise ConfigurationError(f"Conflicting dynamic model field types in {annotation}: "
                                         f"{type_map[option.type].__name__} vs {option.__name__}")
            type_map[option.type] = option

        field = DynamicModelField()
        field.type_map = type_map
        field.types = tuple(type_map.values())
        return field

    @classmethod
    def _analyze_annotation_list(mcs, annotation) -> Field:
        """List[...] -> ListField"""
        field = ListField()
        item_annotation, = annotation.__args__
        field.item_field = mcs._analyze_annotation(item_annotation)
        return field

    @classmethod
    def _analyze_annotation_dict(mcs, annotation) -> Field:
        """Dict[..., ....] -> DictField"""
        field = DictField()
        key_annotation, value_annotation = annotation.__args__
        field.key_field = mcs._analyze_annotation(key_annotation)
        if not field.key_field.atomic:
            raise ConfigurationError(f'DictField keys may only be booleans, numbers or strings: {annotation}')
        field.value_field = mcs._analyze_annotation(value_annotation)
        return field

    @classmethod
    def _build_roles(mcs, cls: Type[Model], bases: List[Type[Model]], own_field_names: Set[str]):
        all_field_names = {field.name for field in cls.__fields__}
        own_requested_roles: Dict[Role, RequestedRoleFields] = {}
        for requested in cls.declare_roles():
            if requested.role in own_requested_roles:
                raise ConfigurationError(f'Role {requested.role.name} configured for {cls.__name__} multiple times')
            own_requested_roles[requested.role] = requested

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

        max_role_code = max((role.code for role in all_roles), default=0)
        default_role_fields = [field.make_output_config() for field in cls.__fields__]
        cls.__role_fields__ = [default_role_fields] * (max_role_code + 1)
        cls.__roles__ = []
        for role, finalized in roles.items():
            field_configs = [field.make_output_config() for field in cls.__fields__ if field.name in finalized.fields]
            cls.__role_fields__[role.code] = field_configs
            cls.__roles__.append(finalized)
