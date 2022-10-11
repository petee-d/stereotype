from __future__ import annotations

import re
from typing import Union, Any, Iterable, Optional, List

from stereotype.fields.annotations import AnnotationResolver
from stereotype.fields.base import Field
from stereotype.utils import Missing, ConfigurationError, PathErrorType, ValidationContextType, Validator


class _AtomicField(Field):
    atomic = True

    def init_from_annotation(self, parser: AnnotationResolver):
        if parser.annotation is not self.type:
            raise parser.incorrect_type(self)


class BoolField(_AtomicField):
    """
    Boolean value (annotation ``bool``), accepting boolean values or true/yes/false/no strings.

    :param default: Means the field isn't required, used as default directly or called if callable
    :param hide_none: If the field's value is None, it will be hidden from serialized output
    :param hide_false: If the field's value is False, it will be hidden from serialized output
    :param primitive_name: Changes the key used to represent the field in serialized data - input or output
    :param to_primitive_name: Changes the key used to represent the field in serialized data - output only
    :param validators: Optional list of validator callbacks - they raise ``ValueError`` if the value is invalid
    """

    __slots__ = Field.__slots__
    type = bool
    type_repr = 'bool'
    empty_value = False

    def __init__(self, *, default: Any = Missing, hide_none: bool = False, hide_false: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 validators: Optional[List[Validator]] = None):
        super().__init__(default=default, hide_none=hide_none, hide_empty=hide_false,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name, validators=validators)

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


class _BaseNumberField(_AtomicField):
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

    def _validate_min_max_value(self, value: Any, _: ValidationContextType) -> Iterable[PathErrorType]:
        if not (self.min_value <= value <= self.max_value):
            yield (), f'Must be between {self.min_value} and {self.max_value}'

    def _validate_min_value(self, value: Any, _: ValidationContextType) -> Iterable[PathErrorType]:
        if value < self.min_value:
            yield (), f'Must be at least {self.min_value}'

    def _validate_max_value(self, value: Any, _: ValidationContextType) -> Iterable[PathErrorType]:
        if value > self.max_value:
            yield (), f'Must be at most {self.max_value}'


class IntField(_BaseNumberField):
    """
    Integer value (annotation ``int``), accepting integer values, whole float values or strings with integer values.

    :param default: Means the field isn't required, used as default directly or called if callable
    :param hide_none: If the field's value is None, it will be hidden from serialized output
    :param hide_zero: If the field's value is 0, it will be hidden from serialized output
    :param primitive_name: Changes the key used to represent the field in serialized data - input or output
    :param to_primitive_name: Changes the key used to represent the field in serialized data - output only
    :param min_value: Validation enforces the number is greater than or equal to this value
    :param max_value: Validation enforces the number is lower than or equal to this value
    :param validators: Optional list of validator callbacks - they raise ``ValueError`` if the value is invalid
    """

    __slots__ = _BaseNumberField.__slots__
    type = int
    type_repr = 'int'
    empty_value = 0

    def __init__(self, *, default: Any = Missing, hide_none: bool = False, hide_zero: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 min_value: Optional[int] = None, max_value: Optional[int] = None,
                 validators: Optional[List[Validator]] = None):
        super().__init__(default=default, hide_none=hide_none, hide_empty=hide_zero,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name, validators=validators)
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
    """
    Floating point value (annotation ``float``), accepting float values, integers or strings with float values.

    :param default: Means the field isn't required, used as default directly or called if callable
    :param hide_none: If the field's value is None, it will be hidden from serialized output
    :param hide_zero: If the field's value is 0.0, it will be hidden from serialized output
    :param primitive_name: Changes the key used to represent the field in serialized data - input or output
    :param to_primitive_name: Changes the key used to represent the field in serialized data - output only
    :param min_value: Validation enforces the number is greater than or equal to this value
    :param max_value: Validation enforces the number is lower than or equal to this value
    :param validators: Optional list of validator callbacks - they raise ``ValueError`` if the value is invalid
    """

    __slots__ = _BaseNumberField.__slots__
    type = float
    type_repr = 'float'
    empty_value = 0.

    def __init__(self, *, default: Any = Missing, hide_none: bool = False, hide_zero: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 min_value: Optional[float] = None, max_value: Optional[float] = None,
                 validators: Optional[List[Validator]] = None):
        super().__init__(default=default, hide_none=hide_none, hide_empty=hide_zero,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name, validators=validators)
        self.min_value = min_value
        self.max_value = max_value
        self._set_min_max_value_validation(min_value, max_value)


class StrField(_AtomicField):
    """
    String value (annotation ``str``), accepting string values, or anything that can be cast to a string.

    :param default: Means the field isn't required, used as default directly or called if callable
    :param hide_none: If the field's value is None, it will be hidden from serialized output
    :param hide_empty: If the field's value is an empty string, it will be hidden from serialized output
    :param primitive_name: Changes the key used to represent the field in serialized data - input or output
    :param to_primitive_name: Changes the key used to represent the field in serialized data - output only
    :param min_length: Validation enforces the string has a minimum number of characters (1 => non-empty)
    :param max_length: Validation enforces the string has a maximum number of characters
    :param choices: Validation enforces the string matches (case-sensitive) one of these choices
    :param regex: Validation enforces the string matches the regular expression
    :param validators: Optional list of validator callbacks - they raise ``ValueError`` if the value is invalid
    """

    __slots__ = _AtomicField.__slots__ + ('min_length', 'max_length', 'choices', 'regex')
    type = str
    type_repr = 'str'
    empty_value = ''

    def __init__(self, *, default: Any = Missing, hide_none: bool = False, hide_empty: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 min_length: int = 0, max_length: Optional[int] = None, choices: Optional[Iterable[str]] = None,
                 regex: str | re.Pattern | None = None, validators: Optional[List[Validator]] = None):
        super().__init__(default=default, hide_none=hide_none, hide_empty=hide_empty,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name, validators=validators)
        if sum([min_length > 0 or max_length is not None, choices is not None, regex is not None]) > 1:
            raise ConfigurationError('Can only validate length, choices or regex; not combinations of these')
        self.min_length = min_length
        self.max_length = max_length
        self.choices = {choice: None for choice in choices} if choices is not None else None  # Sets are not ordered
        self.regex = re.compile(regex) if isinstance(regex, str) else regex
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
        elif regex is not None:
            self.native_validate = self._validate_regex

    def _validate_choices(self, value: str, _: ValidationContextType) -> Iterable[PathErrorType]:
        if value not in self.choices:
            yield (), f'Must be one of: {", ".join(self.choices)}'

    def _validate_min_max_length(self, value: str, _: ValidationContextType) -> Iterable[PathErrorType]:
        if not (self.min_length <= len(value) <= self.max_length):
            if self.min_length == self.max_length:
                yield (), f'Must be exactly {self.min_length} character{"s" if self.min_length > 1 else ""} long'
            else:
                yield (), f'Must be {self.min_length} to {self.max_length} characters long'

    # Note: the validation methods that are put in place of native_validate may not be static
    # noinspection PyMethodMayBeStatic
    def _validate_not_empty(self, value: str, _: ValidationContextType) -> Iterable[PathErrorType]:
        if not value:
            yield (), 'This value cannot be empty'

    def _validate_min_length(self, value: str, _: ValidationContextType) -> Iterable[PathErrorType]:
        if len(value) < self.min_length:
            yield (), f'Must be at least {self.min_length} characters long'

    def _validate_max_length(self, value: str, _: ValidationContextType) -> Iterable[PathErrorType]:
        if len(value) > self.max_length:
            yield (), f'Must be at most {self.max_length} character{"s" if self.max_length > 1 else ""} long'

    def _validate_regex(self, value: str, _: ValidationContextType) -> Iterable[PathErrorType]:
        if not self.regex.match(value):
            case = " (case insensitive)" if self.regex.flags & re.I else ""
            yield (), f'Must match regex `{self.regex.pattern}`{case}'


ATOMIC_TYPE_MAPPING = {
    bool: BoolField,
    int: IntField,
    float: FloatField,
    str: StrField,
}
