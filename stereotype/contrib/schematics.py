from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Optional, Type, cast, Iterable, Sequence, Union

try:
    # Schematics 2
    from schematics.exceptions import (
        CompoundError as SchematicsValidationError,
        DataError as SchematicsConversionError,
    )
except ImportError:  # pragma: no cover
    # Schematics 1
    from schematics.exceptions import (
        ValidationError as SchematicsValidationError,
        ModelConversionError as SchematicsConversionError,
    )
from schematics.models import Model as SchematicsModel

from stereotype.fields.annotations import AnnotationResolver
from stereotype.fields.model import ModelField
from stereotype.roles import DEFAULT_ROLE, Role
from stereotype.utils import (
    Missing,
    ValidationContextType,
    PathErrorType,
    ToPrimitiveContextType,
    ConversionError,
)


class SchematicsModelField(ModelField):
    """
    Field containing a Schematics ``Model`` class, as specified in the annotation.
    Provides a way to combine stereotype and schematics models, e.g., for migrating from schematics in steps.
    Deep copy doesn't work in Schematics 2, works in Schematics 1.

    :param default: Means the field isn't required, should be None or a callable, for example the model's class
    :param hide_none: If the field's value is None, it will be hidden from serialized output
    :param primitive_name: Changes the key used to represent the field in serialized data - input or output
    :param to_primitive_name: Changes the key used to represent the field in serialized data - output only
    """

    def __init__(
        self,
        *,
        default: Any = Missing,
        hide_none: bool = False,
        primitive_name: Optional[str] = Missing,
        to_primitive_name: Optional[str] = Missing
    ):
        super().__init__(
            default=default,
            hide_none=hide_none,
            primitive_name=primitive_name,
            to_primitive_name=to_primitive_name,
        )

        self.type: Type[SchematicsModel] = cast(Type[SchematicsModel], NotImplemented)

    def init_from_annotation(self, parser: AnnotationResolver):
        if not issubclass(parser.annotation, SchematicsModel):
            raise parser.incorrect_type(self)
        self.type = parser.annotation

    def validate(
        self, value: SchematicsModel, context: ValidationContextType
    ) -> Iterable[PathErrorType]:
        try:
            value.validate()  # Cannot propagate the context to schematics
        except SchematicsValidationError as e:
            # to_primitive works for Schematics 2, messages for Schematics 1
            messages = e.to_primitive() if hasattr(e, "to_primitive") else e.messages
            yield from _iterate_validation_errors(messages)

    def copy_value(self, value: Any) -> Any:
        if value is None or value is Missing:
            return value
        return deepcopy(value)

    def to_primitive(
        self,
        value: Any,
        role: Role = DEFAULT_ROLE,
        context: ToPrimitiveContextType = None,
    ) -> Any:
        if value is None or value is Missing:
            return value
        role_str = role.name if role is not DEFAULT_ROLE else None
        value: SchematicsModel
        return value.to_primitive(role_str, context)

    def convert(self, value):
        try:
            return super().convert(value)
        except SchematicsConversionError as e:
            _raise_conversion_error(e)


def _iterate_validation_errors(messages: dict) -> Iterable[PathErrorType]:
    for key, container in messages.items():
        if isinstance(container, list):
            for error in container:
                yield (str(key),), error
        else:
            for path, error in _iterate_validation_errors(container):
                yield (str(key),) + path, error


def _raise_conversion_error(error: SchematicsConversionError) -> None:
    # Get the first error (for conversion, Schematics reports multiple, stereotype just one) and gather its path
    path = []
    first_error_field: Mapping[str, Union[Sequence[str], Mapping]] = error.args[0]
    while isinstance(first_error_field, Mapping):
        path_key, first_error_field = next(iter(first_error_field.items()))
        path.append(path_key)
    first_error_field: Sequence[str]

    # Schematics 1 -> list[str], Schematics 2 -> ConversionError, in both cases a sequence of string-like messages
    first_message = str(first_error_field[0])
    raise ConversionError.new(first_message, *path)
