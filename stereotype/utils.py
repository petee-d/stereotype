from __future__ import annotations

from typing import Union, List, Dict, Tuple, cast, Any, Callable


class _MissingType:
    """A special singleton type - `Missing` should be the only instance in existence."""
    def __bool__(self):
        return False

    def __repr__(self):
        return 'Missing'

    def __copy__(self):
        return Missing  # Singleton instance, shall not be copied

    def __deepcopy__(self, _):
        return Missing  # Singleton instance, shall not be copied


#: Placeholder value for required fields with missing value
#: (i.e., the field doesn't specify a default, no relation to ``Optional``).
#: Validation will always fail if this value is present, i.e. it's never present in valid models.
#:
#: In the unlikely event of needing to check for this value in code, use ``model.field is Missing``.
Missing = _MissingType()


class StereotypeError(Exception):
    pass


class ConfigurationError(StereotypeError, AssertionError):
    pass


# The validation context is an opaque value passed along to custom Field validators and validate_* methods on Models.
# The type alias serves purely as internal documentation, making types easier to read.
ValidationContextType = Any

# The to_primitive context is an opaque value passed along for use in custom Field and Model implementations.
# The type alias serves purely as internal documentation, making types easier to read.
ToPrimitiveContextType = Any

# An error message (second element) with a path of primitive field names leading to the bad data.
PathErrorType = Tuple[Tuple[str, ...], str]

# Receives the validated value as the only argument, raises ValueError if invalid.
Validator = Callable[[Any, ValidationContextType], None]


class DataError(StereotypeError):
    """Encapsulates one or multiple errors that happened during conversion or validation, mapped by field paths."""

    error_list: List[PathErrorType]

    def __init__(self, errors: List[PathErrorType]):
        self.error_list = errors
        super().__init__(self._error_string())

    def _error_string(self) -> str:
        for path, error in self.error_list:
            if not path:
                return error
            return f'{": ".join(path)}: {error}'
        assert self.error_list, 'Cannot create the exception without any errors'

    @property
    def errors(self) -> Dict[str, Union[List[str], dict]]:
        """
        Generates a potentially deeply nested dictionary with errors and their paths.

        Keys in the dictionaries are field (primitive) names.
        Values are either lists of error messages from simple fields, or recursive dictionaries for compound fields.
        """
        errors = {}
        for path, error in self.error_list:
            container = errors
            if not path:
                path = ('_global',)
            for item in path[:-1]:
                value = container.setdefault(item, {})
                if isinstance(value, list):
                    value = container[item] = cast(dict, {'_global': value})
                container = value
            array = container.setdefault(path[-1], [])
            array.append(error)
        return errors

    @classmethod
    def new(cls, message: str, *path: str):
        return cls([(path, message)])

    def wrapped(self, *path: str) -> DataError:
        raise type(self)([(path + original_path, error) for original_path, error in self.error_list])


class ConversionError(DataError, TypeError):
    """Single error created when converting raw data to a Model, caused mostly by failed type coercions."""


class ValidationError(DataError, ValueError):
    """Potentially multiple errors created when validating already converted models."""
