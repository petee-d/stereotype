from __future__ import annotations

from typing import Any, Optional, Type, Iterable, Tuple, Dict, cast

from supermodel.fields.base import Field
from supermodel.model import Model
from supermodel.utils import Missing


class ModelField(Field):
    __slots__ = Field.__slots__ + ('type',)
    atomic = False

    def __init__(self, *, default: Any = Missing, hide_none: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing):
        super().__init__(default=default, hide_none=hide_none,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name)

        self.type: Type[Model] = cast(Type[Model], NotImplemented)
        self.native_validate = self.validate

    def validate(self, value: Any, context: dict) -> Iterable[Tuple[Tuple[str, ...], str]]:
        yield from value.validation_errors(context)

    def type_config_from(self, field: ModelField):
        super().type_config_from(field)
        self.type = field.type

    def convert(self, value: Any) -> Any:
        if value is Missing:
            if self.required:
                return Missing
            return self.default if self.default_factory is None else self.default_factory()
        if value is None:
            return None
        if isinstance(value, Model):
            if not isinstance(value, self.type):
                raise TypeError(f'Supplied type {type(value).__name__}, needs a mapping or {self.type.__name__}')
            return value
        return self.type(value)

    def copy_value(self, value: Any) -> Any:
        if value is None or value is Missing:
            return value
        return value.copy(deep=True)

    def to_primitive(self, value: Any) -> Any:
        if value is None or value is Missing:
            return value
        return value.to_primitive()

    @property
    def type_repr(self):
        return self.type.__name__ if self.type is not NotImplemented else '(unknown)'


class DynamicModelField(Field):
    __slots__ = Field.__slots__ + ('types', 'type_map')
    atomic = False
    type = Model

    def __init__(self, *, default: Any = Missing, hide_none: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing):
        super().__init__(default=default, hide_none=hide_none,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name)

        self.types: Tuple[Type[Model], ...] = NotImplemented
        self.type_map: Dict[str, Type[Model]] = NotImplemented
        self.native_validate = self.validate

    def validate(self, value: Any, context: dict) -> Iterable[Tuple[Tuple[str, ...], str]]:
        yield from value.validation_errors(context)

    def type_config_from(self, field: DynamicModelField):
        super().type_config_from(field)
        self.types = field.types
        self.type_map = field.type_map

    def convert(self, value: Any) -> Any:
        if value is Missing:
            if self.required:
                return Missing
            return self.default if self.default_factory is None else self.default_factory()
        is_model = isinstance(value, Model)
        if is_model and not isinstance(value, self.types):
            raise TypeError(f'Expected {self.type_repr}, got {type(value).__name__}')
        if is_model or value is None:
            return value

        try:
            value_type = value['type']
        except TypeError:
            raise TypeError(f'Expected a mapping with a `type` field, got type {type(value).__name__}')
        except KeyError:
            raise TypeError('Expected a mapping with a `type` field, got no `type` field')
        type_cls = self.type_map.get(value_type, None)
        if type_cls is None:
            raise TypeError(f'Got a mapping with unsupported `type` {value_type!r}')
        return type_cls(value)

    def copy_value(self, value: Any) -> Any:
        if value is None or value is Missing:
            return value
        return value.copy(deep=True)

    def to_primitive(self, value: Any) -> Any:
        if value is None or value is Missing:
            return value
        result = value.to_primitive()
        result['type'] = value.type
        return result

    @property
    def type_repr(self):
        return f'Union[{", ".join(option.__name__ for option in self.types)}]'
