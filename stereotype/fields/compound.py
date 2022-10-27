from __future__ import annotations

from typing import Any, Optional, Iterable, get_args, List

from stereotype.fields.annotations import AnnotationResolver
from stereotype.fields.base import Field, ValidationContextType
from stereotype.roles import Role, DEFAULT_ROLE
from stereotype.utils import Missing, ConfigurationError, ConversionError, PathErrorType, Validator, \
    ToPrimitiveContextType


class _CompoundField(Field):
    __slots__ = Field.__slots__ + ('min_length', 'max_length')
    atomic = False

    def __init__(self, *, default: Any = Missing, hide_none: bool = False, hide_empty: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 min_length: int = 0, max_length: Optional[int] = None, validators: Optional[List[Validator]] = None):
        super().__init__(default=default, hide_none=hide_none, hide_empty=hide_empty,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name, validators=validators)
        self.min_length = min_length
        self.max_length = max_length

    def init_from_annotation(self, parser: AnnotationResolver):
        raise NotImplementedError  # pragma: no cover

    def validate(self, value: Any, context: ValidationContextType) -> Iterable[PathErrorType]:
        if self.min_length > 0:
            if self.max_length is not None:
                if not (self.min_length <= len(value) <= self.max_length):
                    if self.min_length == self.max_length:
                        yield (), f'Provide exactly {self.min_length} item{"s" if self.min_length > 1 else ""}'
                    else:
                        yield (), f'Provide {self.min_length} to {self.max_length} items'
            elif len(value) < self.min_length:
                yield (), f'Provide at least {self.min_length} item{"s" if self.min_length > 1 else ""}'
        elif self.max_length is not None and len(value) > self.max_length:
            yield (), f'Provide at most {self.max_length} item{"s" if self.max_length > 1 else ""}'


class ListField(_CompoundField):
    """
    List value (annotation ``typing.List``), accepting lists of the inner type.

    :param item_field: Optionally allows specifying further options for the type of the list's items
    :param default: Means the field isn't required, should be None, [] or a callable, for example `list`
    :param hide_none: If the field's value is None, it will be hidden from serialized output
    :param hide_empty: If the list is empty, it will be hidden from serialized output
    :param primitive_name: Changes the key used to represent the field in serialized data - input or output
    :param to_primitive_name: Changes the key used to represent the field in serialized data - output only
    :param min_length: Validation enforces the list has a minimum number of items (1 => non-empty)
    :param max_length: Validation enforces the list has a maximum number of items
    :param validators: Optional list of validator callbacks - they raise ``ValueError`` if the value is invalid
    """

    __slots__ = _CompoundField.__slots__ + ('item_field',)
    type = list
    empty_value = []

    def __init__(self, item_field: Field = NotImplemented, *,
                 default: Any = Missing, hide_none: bool = False, hide_empty: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 min_length: int = 0, max_length: Optional[int] = None, validators: Optional[List[Validator]] = None):
        super().__init__(default=default, hide_none=hide_none, hide_empty=hide_empty,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name,
                         min_length=min_length, max_length=max_length, validators=validators)
        self.item_field: Field = item_field
        self.native_validate = self.validate

    def init_from_annotation(self, parser: AnnotationResolver):
        if parser.origin is not list:
            raise parser.incorrect_type(self)
        item_annotation, = get_args(parser.annotation)
        self.item_field = AnnotationResolver(item_annotation).resolve(self.item_field)

    def init_default(self, default: Any):
        if default == self.empty_value:
            default = list
        super().init_default(default)

    def validate(self, value: Any, context: ValidationContextType) -> Iterable[PathErrorType]:
        yield from super().validate(value, context)
        item_validator = self.item_field.validation_errors
        for index, item in enumerate(value):
            for path, error in item_validator(item, context):
                yield (str(index),) + path, error

    def convert(self, value: Any) -> Any:
        if value is Missing:
            return self._fill_missing()
        if value is None:
            return None
        converter = self.item_field.convert
        converted = []
        error_index = 0
        try:
            for error_index, item in enumerate(value):
                converted.append(converter(item))
        except ConversionError as e:
            raise e.wrapped(str(error_index))
        except (TypeError, ValueError) as e:
            raise ConversionError.new(str(e), str(error_index))
        return converted

    def copy_value(self, value: Any) -> Any:
        if value is Missing or value is None:
            return value
        if self.item_field.atomic:
            return list(value)
        item_copy = self.item_field.copy_value
        return [item_copy(item) for item in value]

    def to_primitive(self, value: Any, role: Role = DEFAULT_ROLE, context: ToPrimitiveContextType = None) -> Any:
        if value is None or value is Missing:
            return value
        if not self.item_field.custom_to_primitive:
            return list(value)
        item_to_primitive = self.item_field.to_primitive
        return [item_to_primitive(item, role, context) for item in value]

    @property
    def type_repr(self):
        return f'List[{"?" if self.item_field is NotImplemented else self.item_field.type_repr}]'


class DictField(_CompoundField):
    """
    Dict value (annotation ``typing.Dict``), accepting dicts with applicable keys and values.

    :param key_field: Optionally allows specifying further options for the type of the dict's keys
    :param value_field: Optionally allows specifying further options for the type of the dict's values
    :param default: Means the field isn't required, should be None, {} or a callable, for example `dict`
    :param hide_none: If the field's value is None, it will be hidden from serialized output
    :param hide_empty: If the dict is empty, it will be hidden from serialized output
    :param primitive_name: Changes the key used to represent the field in serialized data - input or output
    :param to_primitive_name: Changes the key used to represent the field in serialized data - output only
    :param min_length: Validation enforces the dict has a minimum number of items (1 => non-empty)
    :param max_length: Validation enforces the dict has a maximum number of items
    :param validators: Optional list of validator callbacks - they raise ``ValueError`` if the value is invalid
    """

    __slots__ = _CompoundField.__slots__ + ('key_field', 'value_field')
    type = dict
    empty_value = {}

    def __init__(self, key_field: Field = NotImplemented, value_field: Field = NotImplemented, *,
                 default: Any = Missing, hide_none: bool = False, hide_empty: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 min_length: int = 0, max_length: Optional[int] = None, validators: Optional[List[Validator]] = None):
        super().__init__(default=default, hide_none=hide_none, hide_empty=hide_empty,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name,
                         min_length=min_length, max_length=max_length, validators=validators)
        self.key_field: Field = key_field
        self.value_field: Field = value_field
        self.native_validate = self.validate

    def init_from_annotation(self, parser: AnnotationResolver):
        if parser.origin is not dict:
            raise parser.incorrect_type(self)
        key_annotation, value_annotation = get_args(parser.annotation)
        self.key_field = AnnotationResolver(key_annotation).resolve(self.key_field)
        if not self.key_field.atomic:
            raise ConfigurationError(f'DictField keys may only be booleans, numbers or strings: {parser!r}')
        self.value_field = AnnotationResolver(value_annotation).resolve(self.value_field)

    def init_default(self, default: Any):
        if default == self.empty_value:
            default = dict
        super().init_default(default)

    def validate(self, value: Any, context: ValidationContextType) -> Iterable[PathErrorType]:
        yield from super().validate(value, context)
        key_validator = self.key_field.validation_errors
        value_validator = self.value_field.validation_errors

        for key, val in value.items():
            for path, error in key_validator(key, context):
                yield (str(key),) + path, error
            for path, error in value_validator(val, context):
                yield (str(key),) + path, error

    def convert(self, value: Any) -> Any:
        if value is Missing:
            return self._fill_missing()
        if value is None:
            return None
        if not isinstance(value, dict):
            raise TypeError(f'Expected a dict, got a {type(value).__name__}')
        key_converter = self.key_field.convert
        value_converter = self.value_field.convert
        error_key = Missing  # An error cannot occur before the first assignment to this, so Missing won't be used
        try:
            return {key_converter(error_key := key): value_converter(val) for key, val in value.items()}
        except ConversionError as e:
            raise e.wrapped(str(error_key))
        except (TypeError, ValueError) as e:
            raise ConversionError.new(str(e), str(error_key))

    def copy_value(self, value: Any) -> Any:
        if value is None or value is Missing:
            return value
        if self.value_field.atomic:
            return dict(value)
        item_to_primitive = self.value_field.copy_value
        return {key: item_to_primitive(val) for key, val in value.items()}

    def to_primitive(self, value: Any, role: Role = DEFAULT_ROLE, context: ToPrimitiveContextType = None) -> Any:
        if value is None or value is Missing:
            return value
        if not self.value_field.custom_to_primitive:
            return dict(value)
        item_to_primitive = self.value_field.to_primitive
        return {key: item_to_primitive(val, role, context) for key, val in value.items()}

    @property
    def type_repr(self):
        key_repr = '?' if self.key_field is NotImplemented else self.key_field.type_repr
        value_repr = '?' if self.value_field is NotImplemented else self.value_field.type_repr
        return f'Dict[{key_repr}, {value_repr}]'
