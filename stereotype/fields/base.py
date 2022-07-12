from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional, Callable, Iterable, TYPE_CHECKING

from stereotype.fields.annotations import AnnotationResolver
from stereotype.roles import DEFAULT_ROLE, Role
from stereotype.utils import Missing, ConfigurationError, PathErrorType, ValidationContextType

if TYPE_CHECKING:  # pragma: no cover
    from stereotype.model import _OutputFieldConfig, _InputFieldConfig, _ValidatedFieldConfig, _ValidatorMethod, \
        _NativeValidator, _SerializableFn


class Field:
    __slots__ = ('name', 'required', 'allow_none', 'default', 'default_factory', 'native_validate', 'validator_method',
                 'hide_none', 'hide_empty', 'primitive_name', 'to_primitive_name', 'serializable')
    type = NotImplemented
    type_repr: str = NotImplemented
    atomic: bool = False
    empty_value = NotImplemented

    def __init__(self, *, default: Any = Missing, hide_none: bool = False, hide_empty: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing):
        """
        :param default: default value (including None) if not present in primitive data, required if omitted
        :param primitive_name: alternative field name for primitive data
        """
        # All NotImplemented *must* be updated later based on annotations
        self.name: str = NotImplemented
        self.allow_none: bool = False
        self.primitive_name: Optional[str] = primitive_name  # Missing falls back to field name
        self.to_primitive_name: Optional[str] = to_primitive_name  # Missing falls back to field name
        if primitive_name is not Missing and to_primitive_name is Missing:
            self.to_primitive_name = primitive_name

        self.native_validate: Optional[_NativeValidator] = None
        self.validator_method: Optional[_ValidatorMethod] = None
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
                raise ConfigurationError(f'Field `{self.name}` is not Optional and cannot use None as default')
        elif self.type is not NotImplemented and not isinstance(self.default, self.type):
            raise ConfigurationError(f'Value `{self.default}` used as field default must be of type {self.type_repr}')

    def copy_field(self):
        """Copies the field definition - explicit Fields must be copied, otherwise subclasses would share them."""
        copied = type(self)()
        for slot in type(self).__slots__:
            value = getattr(self, slot)
            if slot == 'native_validate' and value is not None:
                value = getattr(copied, value.__func__.__name__)
            setattr(copied, slot, value)
        return copied

    def validate(self, value: Any, context: ValidationContextType) -> Iterable[PathErrorType]:
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

    def to_primitive(self, value: Any, role: Role = DEFAULT_ROLE) -> Any:
        return value

    def copy_value(self, value: Any) -> Any:
        return value

    def make_input_config(self) -> _InputFieldConfig:
        return self.name, self.primitive_name, self.convert, (None if self.atomic else self.copy_value)

    def make_validated_config(self) -> _ValidatedFieldConfig:
        return (self.name, self.primitive_name or self.to_primitive_name or self.name, self.allow_none,
                self.native_validate, self.validator_method)

    def make_output_config(self) -> _OutputFieldConfig:
        return (self.name, self.serializable, self.to_primitive if not self.atomic else None,
                self.to_primitive_name, self.hide_none, self.hide_empty, self.empty_value)

    def has_validation(self) -> bool:
        return self.required or not self.allow_none or self.validator_method or self.native_validate

    def __repr__(self):
        type_repr = f'Optional[{self.type_repr}]' if self.allow_none else self.type_repr
        return (
            f'<Field{f" {self.name}" if self.name is not NotImplemented else ""} of type {type_repr}, '
            f'{"required" if self.required else f"default=<{self.default}>"}'
            f'{f", primitive name {self.primitive_name}" if self.primitive_name != self.name else ""}'
            f'{f", to output {self.to_primitive_name}" if self.to_primitive_name != self.primitive_name else ""}>'
        )


class AnyField(Field):
    __slots__ = Field.__slots__ + ('deep_copy',)
    type_repr: str = 'Any'
    atomic = False

    def __init__(self, *, deep_copy: bool = False, default: Any = Missing, hide_none: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing):
        super().__init__(default=default, hide_none=hide_none,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name)
        self.deep_copy = deep_copy

    def init_from_annotation(self, parser: AnnotationResolver):
        if parser.annotation is not Any:
            raise parser.incorrect_type(self)

    def convert(self, value: Any) -> Any:
        if value is Missing:
            return self._fill_missing()
        return deepcopy(value) if self.deep_copy else value

    def copy_value(self, value: Any) -> Any:
        return deepcopy(value)

    def to_primitive(self, value: Any, role: Role = DEFAULT_ROLE) -> Any:
        return deepcopy(value) if self.deep_copy else value
