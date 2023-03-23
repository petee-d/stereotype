from __future__ import annotations

from copy import deepcopy, copy
from typing import Any, Optional, Callable, Iterable, TYPE_CHECKING, List, Tuple

from stereotype.fields.annotations import AnnotationResolver
from stereotype.roles import DEFAULT_ROLE, Role
from stereotype.utils import Missing, ConfigurationError, PathErrorType, ValidationContextType, Validator, \
    ToPrimitiveContextType

if TYPE_CHECKING:  # pragma: no cover
    from stereotype.model import _OutputFieldConfig, _InputFieldConfig, _ValidatedFieldConfig, _ValidatorMethod, \
        _NativeValidator, _SerializableFn


def field_method_overriden(obj, method_name) -> bool:
    return getattr(type(obj), method_name) is not getattr(Field, method_name)


class Field:
    """
    Abstract base class for other field types. Use :class:`AnyField` if type shouldn't be checked.

    :param default: Means the field isn't required, used as default directly or called if callable
    :param hide_none: If the field's value is None, it will be hidden from serialized output
    :param hide_empty: If the field's value is empty_value (varies by field type), it will be hidden
    :param primitive_name: Changes the key used to represent the field in serialized data - input or output
    :param to_primitive_name: Changes the key used to represent the field in serialized data - output only
    :param validators: Optional list of validator callbacks - they raise ``ValueError`` if the value is invalid
    """

    __slots__ = ('name', 'required', 'allow_none', 'default', 'default_factory', 'native_validate', 'validator_method',
                 'validators', 'hide_none', 'hide_empty', 'primitive_name', 'to_primitive_name', 'serializable',
                 'custom_to_primitive')
    type = NotImplemented
    type_repr: str = NotImplemented
    atomic: bool = False
    empty_value = NotImplemented

    def __init__(self, *, default: Any = Missing, hide_none: bool = False, hide_empty: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 validators: Optional[List[Validator]] = None):
        # All NotImplemented *must* be updated later based on annotations
        self.name: str = NotImplemented
        self.allow_none: bool = False
        self.primitive_name: Optional[str] = primitive_name  # Missing falls back to field name
        self.to_primitive_name: Optional[str] = to_primitive_name  # Missing falls back to field name
        if primitive_name is not Missing and to_primitive_name is Missing:
            self.to_primitive_name = primitive_name

        validate_overridden = field_method_overriden(self, 'validate')
        self.native_validate: Optional[_NativeValidator] = self.validate if validate_overridden else None
        self.validator_method: Optional[_ValidatorMethod] = None
        self.validators: Optional[Tuple[Validator, ...]] = tuple(validators) if validators else None
        self.serializable: Optional[_SerializableFn] = None

        # Only user-specifiable options are allowed as arguments to avoid user confusion
        self.required: bool = True
        self.default: Optional[Any] = None
        self.default_factory: Optional[Callable[[], Any]] = None
        if default is not Missing:
            self.init_default(default)
        self.hide_none = hide_none
        assert not (hide_empty and self.empty_value is NotImplemented), f'{type(self)} does not support hide_empty'
        self.hide_empty = hide_empty
        self.custom_to_primitive = field_method_overriden(self, 'to_primitive')

    def init_from_annotation(self, parser: AnnotationResolver):
        """Check this Field type is appropriate for the annotation and load any nested types from it."""
        raise NotImplementedError  # pragma: no cover

    def init_name(self, name: str):
        self.name = name
        if self.primitive_name is Missing:
            self.primitive_name = name
        if self.to_primitive_name is Missing:
            self.to_primitive_name = name

    def init_default(self, default: Any):
        self.required = False
        if callable(default):
            self.default_factory = default
        else:
            self.default = default

    def check_default(self):
        """Check the default is valid input for the field. Called after `init_from_annotation` and `init_name`."""
        if self.required or self.default_factory is not None:
            pass
        elif self.default is None:
            if not self.allow_none:
                raise ConfigurationError("Cannot use None as default on a non-Optional Field")
        elif self.type is not NotImplemented and not isinstance(self.default, self.type):
            raise ConfigurationError(f'Value `{self.default}` used as field default must be of type {self.type_repr}')

    def copy_field(self):
        """
        Copies the field definition - explicit Fields must be copied, otherwise subclasses would share them.
        Any fields where plain `copy.copy` won't be enough should be manually adjusted afterwards.
        """
        copied = copy(self)
        # The native_validate slot contains a method, which would normally remain bound to the old instance
        native_validate = getattr(self, 'native_validate', None)
        if native_validate is not None:
            copied.native_validate = getattr(copied, native_validate.__func__.__name__)
        return copied

    def validation_errors(self, value: Any, context: ValidationContextType) -> Iterable[PathErrorType]:
        if value is Missing or (value is None and not self.allow_none):
            yield (), 'This field is required'
            return
        if self.native_validate is not None and value is not None:
            yield from self.native_validate(value, context)
        if self.validators is not None:
            for validator in self.validators:
                try:
                    validator(value, context)
                except ValueError as e:
                    yield (), str(e)

    def validate(self, value: Any, context: ValidationContextType) -> Iterable[PathErrorType]:
        """Method to override to add native field validation. If not overridden, native_validate will stay None."""
        yield from ()

    def _fill_missing(self):
        if self.required:
            return Missing
        if self.default_factory is None:
            return self.default
        return self.default_factory()

    def convert(self, value: Any) -> Any:
        if value is Missing:
            return self._fill_missing()
        if value is None:
            return None
        return self.type(value)

    def to_primitive(self, value: Any, role: Role = DEFAULT_ROLE, context: ToPrimitiveContextType = None) -> Any:
        return value

    def copy_value(self, value: Any) -> Any:
        return value

    def make_input_config(self) -> _InputFieldConfig:
        return self.name, self.primitive_name, self.convert, (None if self.atomic else self.copy_value)

    def make_validated_config(self) -> _ValidatedFieldConfig:
        return (self.name, self.primitive_name or self.to_primitive_name or self.name, self.allow_none,
                self.validation_errors, self.validator_method)

    def make_output_config(self) -> _OutputFieldConfig:
        # Note this isn't expected to be used if to_primitive_name is None
        return (self, self.name, self.serializable,
                self.to_primitive if self.custom_to_primitive else None, self.to_primitive_name,
                self.hide_none, self.hide_empty, self.empty_value)

    def has_validation(self) -> bool:
        return self.required or not self.allow_none or self.validator_method or self.native_validate or self.validators

    def __repr__(self):
        type_repr = f'Optional[{self.type_repr}]' if self.allow_none else self.type_repr
        return (
            f'<Field{f" {self.name}" if self.name is not NotImplemented else ""} of type {type_repr}, '
            f'{"required" if self.required else f"default=<{self.default}>"}'
            f'{f", primitive name {self.primitive_name}" if self.primitive_name != self.name else ""}'
            f'{f", to output {self.to_primitive_name}" if self.to_primitive_name != self.primitive_name else ""}>'
        )


class AnyField(Field):
    """
    Value of any type (usually annotation ``typing.Any``, but can be anything).

    :param deep_copy: If true, conversion, serialization and copying will use copy.deepcopy for this value
    :param default: Means the field isn't required, used as default directly or called if callable
    :param hide_none: If the field's value is None, it will be hidden from serialized output
    :param primitive_name: Changes the key used to represent the field in serialized data - input or output
    :param to_primitive_name: Changes the key used to represent the field in serialized data - output only
    :param validators: Optional list of validator callbacks - they raise ``ValueError`` if the value is invalid
    """

    __slots__ = Field.__slots__ + ('deep_copy',)
    type = NotImplemented  # There is no appropriate type, NotImplemented is handled specifically
    type_repr: str = 'Any'
    atomic = False

    def __init__(self, *, deep_copy: bool = False, default: Any = Missing, hide_none: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 validators: Optional[List[Validator]] = None):
        super().__init__(default=default, hide_none=hide_none,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name, validators=validators)
        self.deep_copy = deep_copy

    def init_from_annotation(self, parser: AnnotationResolver):
        pass  # Don't require typing.Any, explicit AnyField should allow any typing

    def convert(self, value: Any) -> Any:
        if value is Missing:
            return self._fill_missing()
        return deepcopy(value) if self.deep_copy else value

    def copy_value(self, value: Any) -> Any:
        return deepcopy(value)

    def to_primitive(self, value: Any, role: Role = DEFAULT_ROLE, context: ToPrimitiveContextType = None) -> Any:
        return deepcopy(value) if self.deep_copy else value
