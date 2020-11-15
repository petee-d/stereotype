from __future__ import annotations

from typing import Optional, Tuple, List, Iterable, Type, Set, Callable, Any

from supermodel.fields.base import Field
from supermodel.meta import ModelMeta
from supermodel.roles import Role, RequestedRoleFields, FinalizedRoleFields, DEFAULT_ROLE
from supermodel.utils import Missing, ValidationError, ConversionError


class Model(metaclass=ModelMeta):
    __slots__ = []
    __fields__: List[Field]
    __input_fields__: List[InputFieldConfig]
    __validated_fields__: List[ValidatedFieldConfig]
    __role_fields__: List[List[OutputFieldConfig]]
    __roles__: List[FinalizedRoleFields]

    def __init__(self, raw_data: Optional[dict] = None):
        if self.__input_fields__ is NotImplemented:
            self.__initialize_model__()
        if raw_data is None:
            raw_data = {}
        elif not isinstance(raw_data, dict):
            raise ConversionError([((), f'Supplied type {type(raw_data).__name__}, needs a mapping')])

        for name, primitive_name, convert in self.__input_fields__:
            if primitive_name is None:
                value = Missing
            else:
                value = raw_data.get(primitive_name, Missing)
            try:
                setattr(self, name, convert(value))
            except ConversionError as e:
                raise ConversionError([((primitive_name,) + path, error) for path, error in e.error_list])
            except (TypeError, ValueError) as e:
                raise ConversionError([((primitive_name,), str(e))])

    def to_primitive(self, role: Role = DEFAULT_ROLE):
        if role.code < len(self.__role_fields__):
            fields = self.__role_fields__[role.code]
        elif role.empty_by_default:
            return {}
        else:
            fields = self.__role_fields__[0]

        result = {}
        for name, serializable, atomic, to_primitive, to_primitive_name, hide_none, hide_empty, empty_value in fields:
            if serializable is None:
                value = getattr(self, name)
                if value is Missing or to_primitive_name is None:
                    continue
                if (value is None and hide_none) or (hide_empty and value == empty_value):
                    continue
                result[to_primitive_name] = value if atomic else to_primitive(value)
            else:
                value = serializable(self)
                if value is None and hide_none:
                    continue
                result[to_primitive_name] = value
        return result

    def serialize(self, role: Role = DEFAULT_ROLE):
        return self.to_primitive(role)

    def validate(self, context: Optional[dict] = None):
        errors = list(self.validation_errors(context))
        if errors:
            raise ValidationError(errors)

    def validation_errors(self, context: Optional[dict]) -> Iterable[Tuple[Tuple[str, ...], str]]:
        for name, primitive_name, allow_none, native_validate, validator_method in self.__validated_fields__:
            value = getattr(self, name)
            if value is Missing or (value is None and not allow_none):
                yield (primitive_name,), 'This field is required'
                continue
            if native_validate is not None and value is not None:
                for path, error in native_validate(value, context):
                    yield (primitive_name,) + path, error
            if validator_method is not None:
                try:
                    validator_method(self, value, context)
                except ValueError as e:
                    yield (primitive_name,), str(e)

    @classmethod
    def declare_roles(cls) -> Iterable[RequestedRoleFields]:
        yield from ()

    @classmethod
    def resolve_extra_types(cls) -> Set[Type[Model]]:
        """
        Can be used to return a set of symbols that are not available globally in this model's module, such as
        locally declared other models or models that cannot be imported globally and use `if TYPE_CHECKING`. Simply
        return any such model classes in this class method, importing it locally if needed.
        """
        return set()

    def __getitem__(self, key):
        if key not in self.__slots__:
            raise KeyError(key)  # Avoids getting methods via getitem
        return getattr(self, key)

    def __eq__(self, other: Model):
        if type(self) != type(other):
            return False
        for name, primitive_name, convert in self.__input_fields__:
            if getattr(self, name) != getattr(other, name):
                return False
        return True

    def __repr__(self):
        parts = []
        for field in self.__fields__:
            base = f'{field.name}='
            if field.serializable is not None:
                continue
            value = getattr(self, field.name)
            if field.atomic:
                parts.append(f'{base}{repr(value)}')
            elif field.type is list or field.type is dict:
                if value:
                    if field.type is list:
                        parts.append(f'{base}[({len(value)} items)]')
                    else:
                        parts.append(f'{base}{{({len(value)} items)}}')
                else:
                    parts.append(f'{base}{value!r}')
            elif issubclass(field.type, Model):
                parts.append(f'{base}{type(value).__name__ if isinstance(value, Model) else value}')
            else:
                raise NotImplementedError
        return f'<{self.__class__.__name__} {{' + ', '.join(parts) + '}>'

    def items(self) -> Iterable[Tuple[str, Any]]:
        for name, primitive_name, convert in self.__input_fields__:
            value = getattr(self, name)
            if value is Missing:
                continue
            yield name, value

    @classmethod
    def field_names_for_role(cls, role: Role = DEFAULT_ROLE) -> List[str]:
        if role.code < len(cls.__role_fields__):
            fields = cls.__role_fields__[role.code]
        else:
            fields = [] if role.empty_by_default else cls.__role_fields__[0]
        return [name for name, *_ in fields]


# These rather ugly tuples measurably improve performance compared to accessing field attributes.
# See their usage for the attributes included.
InputFieldConfig = Tuple[str, Optional[str], Callable[[Any], Any]]
ValidatedFieldConfig = Tuple[str, str, bool, Optional[Callable[[Any, dict], Iterable[Tuple[Tuple[str, ...], str]]]],
                             Optional[Callable[[Model, Any, Optional[dict]], None]]]
OutputFieldConfig = Tuple[str, Optional[Callable[[Model], Any]], bool,
                          Callable[[Any], Any], Optional[str], bool, bool, Any]
