from typing import Union, List, Dict, Tuple, cast


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


class DataError(StereotypeError):
    error_list: List[Tuple[Tuple[str, ...], str]]

    def __init__(self, errors: List[Tuple[Tuple[str, ...], str]]):
        self.error_list = errors
        super().__init__(self._error_string())

    def _error_string(self) -> str:
        assert self.error_list, 'Cannot create the exception without any errors'
        for path, error in self.error_list:
            if not path:
                return error
            return f'{": ".join(path)}: {error}'

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


class ValidationError(DataError, ValueError):
    pass


class ConversionError(DataError, TypeError):
    pass
