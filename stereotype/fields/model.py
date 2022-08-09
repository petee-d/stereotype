from __future__ import annotations

from typing import Any, Optional, Type, Iterable, Tuple, Dict, cast, Union, get_args, List

from stereotype.fields.annotations import AnnotationResolver
from stereotype.fields.base import Field
from stereotype.model import Model
from stereotype.roles import Role, DEFAULT_ROLE
from stereotype.utils import Missing, ConfigurationError, PathErrorType, ValidationContextType, Validator, \
    ToPrimitiveContextType


class ModelField(Field):
    __slots__ = Field.__slots__ + ('type',)
    atomic = False
    empty_value = {}

    def __init__(self, *, default: Any = Missing, hide_none: bool = False, hide_empty: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 validators: Optional[List[Validator]] = None):
        """
        Field containing another specific Model, as specified in the annotation.
        :param default: Means the field isn't required, should be None or a callable, for example the model's class
        :param hide_none: If the field's value is None, it will be hidden from serialized output
        :param hide_empty: If the model serializes as an empty dict, it will be hidden from serialized output
        :param primitive_name: Changes the key used to represent the field in serialized data - input or output
        :param to_primitive_name: Changes the key used to represent the field in serialized data - output only
        :param validators: Optional list of validator callbacks - they receive value and raise ValueError if invalid
        """
        super().__init__(default=default, hide_none=hide_none, hide_empty=hide_empty,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name, validators=validators)
        self.type: Type[Model] = cast(Type[Model], NotImplemented)
        self.native_validate = self.validate

    def init_from_annotation(self, parser: AnnotationResolver):
        if not issubclass(parser.annotation, Model):
            raise parser.incorrect_type(self)
        self.type = parser.annotation

    def validate(self, value: Model, context: ValidationContextType) -> Iterable[PathErrorType]:
        yield from value.validation_errors(context)

    def convert(self, value: Any) -> Any:
        if value is Missing:
            if self.required:
                return Missing
            return self.default if self.default_factory is None else self.default_factory()
        if value is None:
            return None
        if isinstance(value, self.type):
            return value
        if not isinstance(value, dict):
            raise TypeError(f'Supplied type {type(value).__name__}, needs a mapping or {self.type.__name__}')
        return self.type(value)

    def copy_value(self, value: Any) -> Any:
        if value is None or value is Missing:
            return value
        return value.copy(deep=True)

    def to_primitive(self, value: Any, role: Role = DEFAULT_ROLE, context: ToPrimitiveContextType = None) -> Any:
        if value is None or value is Missing:
            return value
        return value.to_primitive(role, context)

    @property
    def type_repr(self):
        return self.type.__name__ if self.type is not NotImplemented else '(unknown)'


class DynamicModelField(Field):
    __slots__ = Field.__slots__ + ('types', 'type_map')
    atomic = False
    type = Model

    def __init__(self, *, default: Any = Missing, hide_none: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing,
                 validators: Optional[List[Validator]] = None):
        """
        Field containing one of models recognized by their `type`, specified as a `typing.Union` of Model subclasses.
        :param default: Means the field isn't required, should be None or a callable, for example a model's class
        :param hide_none: If the field's value is None, it will be hidden from serialized output
        :param primitive_name: Changes the key used to represent the field in serialized data - input or output
        :param to_primitive_name: Changes the key used to represent the field in serialized data - output only
        :param validators: Optional list of validator callbacks - they receive value and raise ValueError if invalid
        """
        super().__init__(default=default, hide_none=hide_none,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name, validators=validators)
        self.types: Tuple[Type[Model], ...] = NotImplemented
        self.type_map: Dict[str, Type[Model]] = NotImplemented
        self.native_validate = self.validate

    def init_from_annotation(self, parser: AnnotationResolver):
        if parser.origin is not Union:
            raise parser.incorrect_type(self)
        options = get_args(parser.annotation)

        if not all(issubclass(option, Model) for option in options):
            raise ConfigurationError(f'Union Model fields can only be Optional or Union of Model subclass types, '
                                     f'got {parser!r}')

        type_map = {}
        for option in options:
            if not hasattr(option, 'type'):
                raise ConfigurationError(f"Model {option.__name__} used in a dynamic model field {parser!r} but "
                                         f"does not define a non-type-annotated string `type` field")
            if type(option.type).__name__ == 'member_descriptor':
                raise ConfigurationError(f"Model {option.__name__} used in a dynamic model field {parser!r} but its "
                                         f"`type` field has a type annotation making it a field, must be an attribute")
            if not isinstance(option.type, str):
                raise ConfigurationError(f"Model {option.__name__} used in a dynamic model field {parser!r} but its "
                                         f"`type` field {option.type} is not a string")
            if option.type in type_map:
                raise ConfigurationError(f"Conflicting dynamic model field types in {parser!r}: "
                                         f"{type_map[option.type].__name__} vs {option.__name__}")
            type_map[option.type] = option

        self.type_map = type_map
        self.types = tuple(type_map.values())

    def validate(self, value: Any, context: ValidationContextType) -> Iterable[PathErrorType]:
        yield from value.validation_errors(context)

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

    def to_primitive(self, value: Any, role: Role = DEFAULT_ROLE, context: ToPrimitiveContextType = None) -> Any:
        if value is None or value is Missing:
            return value
        result = value.to_primitive(role, context)
        result['type'] = value.type
        return result

    @property
    def type_repr(self):
        return f'Union[{", ".join(option.__name__ for option in self.types)}]'
