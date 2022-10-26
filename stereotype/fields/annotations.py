from __future__ import annotations

import types
from typing import Any, Optional, TYPE_CHECKING, Union, get_origin, get_args

from stereotype.utils import ConfigurationError

if TYPE_CHECKING:  # pragma: no cover
    from stereotype.fields.base import Field

try:
    _py310_union_type = types.UnionType  # Python 3.10 or above
except AttributeError:  # pragma: no cover
    _py310_union_type = NotImplemented  # Python 3.9 or below


class AnnotationResolver:
    __slots__ = ['annotation', 'origin', 'optional']

    def __init__(self, annotation: Any):
        """Create helper capable of resolving annotations to Fields, automatically unwrap Optional."""
        self.annotation = annotation
        self.origin = get_origin(annotation)
        self.optional = False
        self._unwrap_optional()

    def _unwrap_optional(self):
        if not self.is_union_origin():
            return

        options = get_args(self.annotation)
        non_none = [option for option in options if option not in (type(None),)]
        if len(non_none) == len(options):
            return  # A Union of non-optional types

        self.optional = True
        if len(non_none) == 1:
            self.annotation = non_none[0]
        else:
            # There are more elements in the Union, remove None from it
            self.annotation = Union[tuple(non_none)]
        self.origin = get_origin(self.annotation)

    def __repr__(self):
        if self.origin is None and hasattr(self.annotation, '__name__'):
            return self.annotation.__name__
        return repr(self.annotation)

    def resolve(self, explict_field: Optional[Field] = None) -> Field:
        if explict_field is None or explict_field is NotImplemented:
            field = self.auto_resolve()
        else:
            field = explict_field.copy_field()  # So that subclasses don't share the same Field and leak validation
        field.init_from_annotation(self)
        field.allow_none = self.optional
        return field

    def auto_resolve(self) -> Field:
        """Attempt to recognize the annotation and create the corresponding Field instance."""
        from stereotype import Model, ListField, DictField, ModelField, DynamicModelField, AnyField
        from stereotype.fields.atomic import ATOMIC_TYPE_MAPPING

        if self.origin is not None:
            if self.origin is list:
                return ListField()
            if self.origin is dict:
                return DictField()
            if self.is_union_origin():
                return DynamicModelField()  # Cannot be Optional at this point, taken care of in init
        elif self.annotation is Any:
            return AnyField()

        elif atomic_field := ATOMIC_TYPE_MAPPING.get(self.annotation):
            return atomic_field()

        elif issubclass(self.annotation, Model):
            return ModelField()

        raise ConfigurationError(f'Unrecognized field annotation {self!r} (may need an explicit Field)')

    def is_union_origin(self):
        return self.origin is Union or (_py310_union_type is not NotImplemented and self.origin is _py310_union_type)

    def incorrect_type(self, field: Field) -> ConfigurationError:
        hint = ''
        try:
            hint = f', should use {type(self.auto_resolve()).__name__}'
        except ConfigurationError:
            pass
        return ConfigurationError(f'{type(field).__name__} cannot be used for annotation {self!r}{hint}')
