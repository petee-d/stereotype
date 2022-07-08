from __future__ import annotations

from typing import Union, List, Dict, Tuple, cast, Any


class _MissingType:
    def __bool__(self):
        return False

    def __repr__(self):
        return 'Missing'


Missing = _MissingType()


class StereotypeError(Exception):
    pass


class ConfigurationError(StereotypeError, AssertionError):
    pass


ValidationContextType = Any  # This serves purely as internal documentation, making types easier to read
PathErrorType = Tuple[Tuple[str, ...], str]


class DataError(StereotypeError):
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


class ValidationError(DataError, ValueError):
    pass


class ConversionError(DataError, TypeError):
    pass
