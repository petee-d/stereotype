from typing import Any, Optional, Iterable, Tuple

from supermodel.fields.base import Field
from supermodel.utils import Missing


class _CompoundField(Field):
    __slots__ = Field.__slots__ + ('min_length', 'max_length')
    atomic = False

    def __init__(self, *, default: Any = Missing, hide_none: bool = False, hide_empty: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 min_length: int = 0, max_length: Optional[int] = None):
        super().__init__(default=default, hide_none=hide_none, hide_empty=hide_empty,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name)
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, value: Any, context: dict) -> Iterable[Tuple[Tuple[str, ...], str]]:
        yield from super().validate(value, context)
        if value is Missing or value is None:
            return

        if self.min_length > 0:
            if self.max_length is not None:
                if not (self.min_length <= len(value) <= self.max_length):
                    if self.min_length == self.max_length:
                        yield (), f'Provide exactly {self.min_length} item{"s" if self.min_length > 1 else ""}'
                    else:
                        yield (), f'Provide {self.min_length} to {self.max_length} items'
                    return
            elif len(value) < self.min_length:
                yield (), f'Provide at least {self.min_length} item{"s" if self.min_length > 1 else ""}'
                return
        elif self.max_length is not None and len(value) > self.max_length:
            yield (), f'Provide at most {self.max_length} item{"s" if self.max_length > 1 else ""}'
            return


class ListField(_CompoundField):
    __slots__ = Field.__slots__ + ('item_field',)
    type = list
    empty_value = []

    def __init__(self, item_field: Field = NotImplemented, *,
                 default: Any = Missing, hide_none: bool = False, hide_empty: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 min_length: int = 0, max_length: Optional[int] = None):
        super().__init__(default=default, hide_none=hide_none, hide_empty=hide_empty,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name,
                         min_length=min_length, max_length=max_length)
        self.item_field: Field = item_field

    def validate(self, value: Any, context: dict) -> Iterable[Tuple[Tuple[str, ...], str]]:
        yield from super().validate(value, context)
        if value is None or value is Missing:
            return
        for index, item in enumerate(value):
            for path, error in self.item_field.validate(item, context):
                yield (str(index),) + path, error

    def type_config_from(self, field: 'ListField'):
        super().type_config_from(field)
        if self.item_field is NotImplemented:
            self.item_field: Field = field.item_field
        else:
            self.item_field.type_config_from(field.item_field)

    def convert(self, value: Any) -> Any:
        if value is Missing:
            return self._fill_missing()
        if value is None:
            return None
        converter = self.item_field.convert
        return [converter(item) for item in value]

    def to_primitive(self, value: Any) -> Any:
        if value is None or value is Missing:
            return value
        if self.item_field.atomic:
            return list(value)
        item_to_primitive = self.item_field.to_primitive
        return [item_to_primitive(item) for item in value]

    @property
    def type_repr(self):
        return f'List[{self.item_field.type_repr}]'


class DictField(_CompoundField):
    __slots__ = Field.__slots__ + ('key_field', 'value_field')
    type = dict
    empty_value = {}

    def __init__(self, key_field: Field = NotImplemented, value_field: Field = NotImplemented, *,
                 default: Any = Missing, hide_none: bool = False, hide_empty: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 min_length: int = 0, max_length: Optional[int] = None):
        super().__init__(default=default, hide_none=hide_none, hide_empty=hide_empty,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name,
                         min_length=min_length, max_length=max_length)
        self.key_field: Field = key_field
        self.value_field: Field = value_field

    def validate(self, value: Any, context: dict) -> Iterable[Tuple[Tuple[str, ...], str]]:
        yield from super().validate(value, context)
        if not value:
            return
        for key, val in value.items():
            for path, error in self.key_field.validate(key, context):
                yield (str(key),) + path, error
            for path, error in self.value_field.validate(val, context):
                yield (str(key),) + path, error

    def type_config_from(self, field: 'DictField'):
        super().type_config_from(field)
        if self.key_field is NotImplemented:
            self.key_field: Field = field.key_field
        else:
            self.key_field.type_config_from(field.key_field)
        if self.value_field is NotImplemented:
            self.value_field: Field = field.value_field
        else:
            self.value_field.type_config_from(field.value_field)

    def convert(self, value: Any) -> Any:
        if value is Missing:
            return self._fill_missing()
        if value is None:
            return None
        if not isinstance(value, dict):
            raise TypeError(f'Expected a dict, got a {type(value).__name__}')
        key_converter = self.key_field.convert
        value_converter = self.value_field.convert
        return {key_converter(key): value_converter(val) for key, val in value.items()}

    def to_primitive(self, value: Any) -> Any:
        if value is None or value is Missing:
            return value
        if self.value_field.atomic:
            return dict(value)
        item_to_primitive = self.value_field.to_primitive
        return {key: item_to_primitive(val) for key, val in value.items()}

    @property
    def type_repr(self):
        return f'Dict[{self.key_field.type_repr}, {self.value_field.type_repr}]'
