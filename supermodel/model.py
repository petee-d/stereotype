from __future__ import annotations

from typing import Optional, Tuple, List, Iterable, Type, Set

from supermodel.fields.base import Field
from supermodel.meta import ModelMeta
from supermodel.roles import Role, RequestedRoleFields, FinalizedRoleFields
from supermodel.utils import Missing, ValidationError, ConversionError


class Model(metaclass=ModelMeta):
    __slots__ = []
    __fields__: List[Field]
    __input_fields__: List[Field]
    __role_fields__: List[List[Field]]
    __roles__: List[FinalizedRoleFields]

    def __init__(self, raw_data: Optional[dict] = None):
        if self.__input_fields__ is NotImplemented:
            self.__initialize_model__()
        if raw_data is None:
            raw_data = {}
        elif not isinstance(raw_data, dict):
            raise ConversionError([((), f'Supplied type {type(raw_data).__name__}, needs a mapping')])

        for field in self.__input_fields__:
            if field.primitive_name is None:
                value = Missing
            else:
                value = raw_data.get(field.primitive_name, Missing)
            try:
                setattr(self, field.name, field.convert(value))
            except ConversionError as e:
                raise ConversionError([((field.primitive_name,) + path, error) for path, error in e.error_list])
            except (TypeError, ValueError) as e:
                raise ConversionError([((field.primitive_name,), str(e))])

    def to_primitive(self, role: Optional[Role] = None):
        if role is None:
            fields = self.__fields__
        elif role.code < len(self.__role_fields__):
            fields = self.__role_fields__[role.code]
        elif role.empty_by_default:
            return {}
        else:
            fields = self.__fields__
        result = {}
        for field in fields:
            if field.serializable is None:
                value = getattr(self, field.name)
                if value is Missing or field.to_primitive_name is None:
                    continue
                if (value is None and field.hide_none) or (field.hide_empty and value == field.empty_value):
                    continue
                result[field.to_primitive_name] = value if field.atomic else field.to_primitive(value)
            else:
                value = field.serializable(self)
                if value is None and field.hide_none:
                    continue
                result[field.to_primitive_name] = value
        return result

    def serialize(self, role: Optional[Role] = None):
        return self.to_primitive(role)

    def validate(self, context: Optional[dict] = None):
        errors = list(self.validation_errors(context))
        if errors:
            raise ValidationError(errors)

    def validation_errors(self, context: Optional[dict]) -> Iterable[Tuple[Tuple[str, ...], str]]:
        for field in self.__input_fields__:
            value = getattr(self, field.name)
            had_native_errors = False
            for path, error in field.validate(value, context):
                had_native_errors = True
                yield (field.primitive_name,) + path, error
            if field.validator_method is not None and not had_native_errors:
                try:
                    field.validator_method(self, value, context)
                except ValueError as e:
                    yield (field.primitive_name,), str(e)

    @classmethod
    def declare_roles(cls) -> Iterable[RequestedRoleFields]:
        yield from ()

    @classmethod
    def resolve_extra_types(cls) -> Set[Type[Model]]:
        return set()

    def __getitem__(self, key):
        if key not in self.__slots__:
            raise KeyError(key)  # Avoids getting methods via getitem
        return getattr(self, key)

    def __eq__(self, other: Model):
        if type(self) != type(other):
            return False
        for field in self.__input_fields__:
            if getattr(self, field.name) != getattr(other, field.name):
                return False
        return True

    def __repr__(self):
        parts = []
        for field in self.__input_fields__:
            base = f'{field.name}='
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
