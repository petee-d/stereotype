from copy import deepcopy
from typing import Any, Optional, Type, cast, Iterable

from schematics.exceptions import ValidationError as SchematicsValidationError
from schematics.models import Model as SchematicsModel

from stereotype.fields.annotations import AnnotationResolver
from stereotype.fields.model import ModelField
from stereotype.roles import DEFAULT_ROLE, Role
from stereotype.utils import Missing, ValidationContextType, PathErrorType, ToPrimitiveContextType


class SchematicsModelField(ModelField):
    def __init__(self, *, default: Any = Missing, hide_none: bool = False,
                 primitive_name: Optional[str] = Missing, to_primitive_name: Optional[str] = Missing):
        super().__init__(default=default, hide_none=hide_none,
                         primitive_name=primitive_name, to_primitive_name=to_primitive_name)

        self.type: Type[SchematicsModel] = cast(Type[SchematicsModel], NotImplemented)
        self.native_validate = self.validate

    def init_from_annotation(self, parser: AnnotationResolver):
        if not issubclass(parser.annotation, SchematicsModel):
            raise parser.incorrect_type(self)
        self.type = parser.annotation

    def validate(self, value: SchematicsModel, context: ValidationContextType) -> Iterable[PathErrorType]:
        try:
            value.validate()  # Cannot propagate the context to schematics
        except SchematicsValidationError as e:
            yield from _iterate_validation_errors(e.messages)

    def copy_value(self, value: Any) -> Any:
        if value is None or value is Missing:
            return value
        return deepcopy(value)

    def to_primitive(self, value: Any, role: Role = DEFAULT_ROLE, context: ToPrimitiveContextType = None) -> Any:
        if value is None or value is Missing:
            return value
        role_str = role.name if role is not DEFAULT_ROLE else None
        value: SchematicsModel
        return value.to_primitive(role_str, context)


def _iterate_validation_errors(messages: dict) -> Iterable[PathErrorType]:
    for key, container in messages.items():
        if isinstance(container, list):
            for error in container:
                yield (key,), error
        else:
            for path, error in _iterate_validation_errors(container):
                yield (key,) + path, error
