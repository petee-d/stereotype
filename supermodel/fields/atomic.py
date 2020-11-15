from typing import Union, Any, Iterable, Tuple, Optional

from supermodel.fields.base import Field
from supermodel.utils import Missing, ConfigurationError


class BoolField(Field):
    __slots__ = Field.__slots__
    type = bool
    type_repr = 'bool'
    empty_value = False

    def __init__(self, *, default: Any = Missing, hide_none: bool = False, hide_false: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing):
        super().__init__(default=default, hide_none=hide_none, hide_empty=hide_false,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name)

    def convert(self, value: Any) -> Any:
        if value is Missing:
            return self._fill_missing()
        if value is None:
            return None
        if value is False or value is True:
            return value
        if value in {'true', 'True', 'yes', 'Yes'}:
            return True
        if value in {'false', 'False', 'no', 'No'}:
            return False
        raise TypeError('Value must be a boolean or a true/false/yes/no string value')


class _BaseNumberField(Field):
    __slots__ = Field.__slots__ + ('min_value', 'max_value')
    min_value: Union[int, float, None]
    max_value: Union[int, float, None]

    def _set_min_max_value_validation(self, min_value: Union[int, float, None], max_value: Union[int, float, None]):
        if min_value is not None and max_value is not None:
            self.native_validate = self._validate_min_max_value
        elif min_value is not None:
            self.native_validate = self._validate_min_value
        elif max_value is not None:
            self.native_validate = self._validate_max_value

    def _validate_min_max_value(self, value: Any, context: dict) -> Iterable[Tuple[Tuple[str, ...], str]]:
        if not (self.min_value <= value <= self.max_value):
            yield (), f'Must be between {self.min_value} and {self.max_value}'

    def _validate_min_value(self, value: Any, context: dict) -> Iterable[Tuple[Tuple[str, ...], str]]:
        if value < self.min_value:
            yield (), f'Must be at least {self.min_value}'

    def _validate_max_value(self, value: Any, context: dict) -> Iterable[Tuple[Tuple[str, ...], str]]:
        if value > self.max_value:
            yield (), f'Must be at most {self.max_value}'


class IntField(_BaseNumberField):
    __slots__ = _BaseNumberField.__slots__
    type = int
    type_repr = 'int'
    empty_value = 0

    def __init__(self, *, default: Any = Missing, hide_none: bool = False, hide_zero: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 min_value: Optional[int] = None, max_value: Optional[int] = None):
        super().__init__(default=default, hide_none=hide_none, hide_empty=hide_zero,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name)
        self.min_value = min_value
        self.max_value = max_value
        self._set_min_max_value_validation(min_value, max_value)

    def convert(self, value: Any) -> Any:
        if value is Missing:
            return self._fill_missing()
        if value is None:
            return None
        if isinstance(value, float) and value != int(value):
            raise TypeError(f'Numeric value {value} is not an integer')
        try:
            return int(value)
        except (ValueError, TypeError):
            raise TypeError(f'Value {value!r} is not an integer number')


class FloatField(_BaseNumberField):
    __slots__ = _BaseNumberField.__slots__
    type = float
    type_repr = 'float'
    empty_value = 0.

    def __init__(self, *, default: Any = Missing, hide_none: bool = False, hide_zero: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 min_value: Optional[float] = None, max_value: Optional[float] = None):
        super().__init__(default=default, hide_none=hide_none, hide_empty=hide_zero,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name)
        self.min_value = min_value
        self.max_value = max_value
        self._set_min_max_value_validation(min_value, max_value)


class StrField(Field):
    __slots__ = Field.__slots__ + ('min_length', 'max_length', 'choices')
    type = str
    type_repr = 'str'
    empty_value = ''

    def __init__(self, *, default: Any = Missing, hide_none: bool = False, hide_empty: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 min_length: int = 0, max_length: Optional[int] = None, choices: Optional[Iterable[str]] = None):
        super().__init__(default=default, hide_none=hide_none, hide_empty=hide_empty,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name)
        if (min_length > 0 or max_length is not None) and choices is not None:
            raise ConfigurationError('Cannot use min_length or max_length together with choices')
        self.min_length = min_length
        self.max_length = max_length
        self.choices = {choice: None for choice in choices} if choices is not None else None  # Sets are not ordered
        if self.choices is not None:
            self.native_validate = self._validate_choices
        elif min_length > 0 and max_length is not None:
            self.native_validate = self._validate_min_max_length
        elif min_length == 1:
            self.native_validate = self._validate_not_empty
        elif min_length > 0:
            self.native_validate = self._validate_min_length
        elif max_length is not None:
            self.native_validate = self._validate_max_length

    def _validate_choices(self, value: str, context: dict) -> Iterable[Tuple[Tuple[str, ...], str]]:
        if value not in self.choices:
            yield (), f'Must be one of: {", ".join(self.choices)}'

    def _validate_min_max_length(self, value: str, context: dict) -> Iterable[Tuple[Tuple[str, ...], str]]:
        if not (self.min_length <= len(value) <= self.max_length):
            if self.min_length == self.max_length:
                yield (), f'Must be exactly {self.min_length} character{"s" if self.min_length > 1 else ""} long'
            else:
                yield (), f'Must be {self.min_length} to {self.max_length} characters long'

    def _validate_not_empty(self, value: str, context: dict) -> Iterable[Tuple[Tuple[str, ...], str]]:
        if not value:
            yield (), f'This value cannot be empty'

    def _validate_min_length(self, value: str, context: dict) -> Iterable[Tuple[Tuple[str, ...], str]]:
        if len(value) < self.min_length:
            yield (), f'Must be at least {self.min_length} characters long'

    def _validate_max_length(self, value: str, context: dict) -> Iterable[Tuple[Tuple[str, ...], str]]:
        if len(value) > self.max_length:
            yield (), f'Must be at most {self.max_length} character{"s" if self.max_length > 1 else ""} long'


ATOMIC_TYPE_MAPPING = {
    bool: BoolField,
    int: IntField,
    float: FloatField,
    str: StrField,
}
