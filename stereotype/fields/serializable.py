from __future__ import annotations

from typing import Callable, Any, Optional, TYPE_CHECKING

from stereotype.fields.annotations import AnnotationResolver
from stereotype.fields.base import Field
from stereotype.utils import Missing

if TYPE_CHECKING:  # pragma: no cover
    from stereotype.model import Model


class SerializableField(Field):
    type_repr: str = 'serializable'

    def __init__(self, func: Callable[[Model], Any] = Missing, *,
                 hide_none: bool = False, to_primitive_name: str = Missing):
        super().__init__(hide_none=hide_none, to_primitive_name=to_primitive_name)
        self.serializable = func

    def init_from_annotation(self, parser: AnnotationResolver):
        raise NotImplementedError  # pragma: no cover


def serializable(func: Optional[Callable[[Model], Any]] = None, *, hide_none: bool = False,
                 to_primitive_name: str = Missing):
    """Decorator that turns properties or methods to output-only fields that are calculated from other fields."""

    def serializable_wrapper(wrapped_func: Callable[[Model], Any]):
        # Support wrapping properties, this allows for better type checking
        if isinstance(wrapped_func, property):
            wrapped_func = wrapped_func.fget
        field = SerializableField(wrapped_func, hide_none=hide_none, to_primitive_name=to_primitive_name)
        wrapped_func.__field__ = field
        return property(wrapped_func)

    if func is not None:
        assert callable(func), 'The positional argument `func` of `serializable` is only for usage without a call'
        return serializable_wrapper(func)

    return serializable_wrapper
