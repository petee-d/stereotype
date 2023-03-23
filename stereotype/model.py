from __future__ import annotations

from typing import Optional, Tuple, List, Iterable, Type, Set, Any, Callable

from stereotype.fields.base import Field
from stereotype.meta import ModelMeta
from stereotype.roles import Role, RequestedRoleFields, FinalizedRoleFields, DEFAULT_ROLE
from stereotype.utils import Missing, ValidationError, ConversionError, PathErrorType, ValidationContextType


class Model(metaclass=ModelMeta):
    """
    The base class for all your models.

    May inherit from other models, but if inheriting from multiple Models, all but one of the bases must be marked
    as abstract by adding the attribute ``__abstract__ = True``.

    Class attributes will become fields (deserialized, validated, serialized) if they:

    * are a public attribute (i.e. not prefixed with ``_``)
    * they have a type hint, unless that type hint is wrapped in ``ClassVar``
    """

    __slots__ = []
    # Don't use these fields in external code directly, they may not be initialized!
    __fields__: List[Field]
    __input_fields__: List[_InputFieldConfig]
    __validated_fields__: List[_ValidatedFieldConfig]
    __role_fields__: List[List[_OutputFieldConfig]]
    __roles__: List[FinalizedRoleFields]
    __gettable__: Set[str]

    def __init__(self, raw_data: Optional[dict] = None):
        """
        Constructs an instance of this Model from input data. Does not perform validation,
        but the conversion may raise a :class:`ConversionError` for a single field with a bad value.

        :param raw_data: Input data to convert, a dictionary with string keys and values corresponding to the fields.
        """
        if self.__input_fields__ is NotImplemented:
            self.__initialize_model__()
        if raw_data is None:
            raw_data = {}
        elif not isinstance(raw_data, dict):
            raise ConversionError.new(f'Supplied type {type(raw_data).__name__}, needs a mapping')

        for name, primitive_name, convert, copy_value in self.__input_fields__:
            if primitive_name is None:
                value = Missing
            else:
                value = raw_data.get(primitive_name, Missing)
            try:
                setattr(self, name, convert(value))
            except ConversionError as e:
                raise e.wrapped(primitive_name)
            except (TypeError, ValueError) as e:
                raise ConversionError.new(str(e), primitive_name)

    def to_primitive(self, role: Role = DEFAULT_ROLE, context=None):
        """
        Creates raw data from this Model, creating a copy of the data it was initialized with.

        :param role: Can be used together with declare_roles to exclude fields for certain roles.
        :param context: Optional value opaque to stereotype, useful for serializing custom field types.
        """
        if role.code < len(self.__role_fields__):
            fields = self.__role_fields__[role.code]
        elif role.empty_by_default:
            return {}
        else:
            fields = self.__role_fields__[0]

        result = {}
        for _, name, serializable, to_primitive, to_primitive_name, hide_none, hide_empty, empty_value in fields:
            if serializable is None:
                value = getattr(self, name)
                if value is Missing:
                    continue
                converted = to_primitive(value, role, context) if to_primitive is not None else value
                if (converted is None and hide_none) or (hide_empty and converted == empty_value):
                    continue
                result[to_primitive_name] = converted
            else:
                value = serializable(self)
                if value is None and hide_none:
                    continue
                result[to_primitive_name] = value
        return result

    serialize = to_primitive

    def validate(self, context=None):
        """
        Validates data, raising a :class:`ValidationError` with potentially multiple error messages,
        mapped by field paths.

        Validation catches: fields without defaults missing in data, None in non-Optional fields and failing validators
        (whether native Field validation options or custom validate_* methods).

        :param context: Optional value opaque to stereotype, passed to any custom validation methods (validate_*).
        """
        errors = list(self.validation_errors(context))
        if errors:
            raise ValidationError(errors)

    def validation_errors(self, context=None) -> Iterable[PathErrorType]:
        """
        Validates data, yielding errors one by one, each with a field path.

        Validation catches: fields without defaults missing in data, None in non-Optional fields and failing validators
        (whether native Field validation options, custom Field validators or custom validate_* methods).

        :param context: Optional value opaque to stereotype, passed to Field validators and validate_* Model methods.
        """
        for name, input_name, allow_none, validation_errors, validator_method in self.__validated_fields__:
            value = getattr(self, name)
            for path, error in validation_errors(value, context):
                yield (input_name,) + path, error
            if validator_method is not None and value is not Missing and (value is not None or allow_none):
                try:
                    validator_method(self, value, context)
                except ValueError as e:
                    yield (input_name,), str(e)

    @classmethod
    def declare_roles(cls) -> Iterable[RequestedRoleFields]:
        """
        Override to specify which fields are serialized for particular roles.

        Define a :class:`stereotype.Role` globally, like:  ``MY_ROLE = Role('my')``

        Then in this class method do for example:          ``yield MY_ROLE.blacklist(cls.my_field)``
        """
        yield from ()

    @classmethod
    def resolve_extra_types(cls) -> Set[Type[Model]]:
        """
        Override to provide a set of symbols that are not available globally in this model's module, such as
        locally declared other models or models that cannot be imported globally and use ``if TYPE_CHECKING``.
        Simply return any such model classes in this class method, importing them locally if needed.

        If inheriting from a Model that implements this, use ``return {...} | super().resolve_extra_types()``
        """
        return set()

    def __getitem__(self, key):
        if key not in self.__gettable__:
            raise KeyError(key)  # Avoids getting methods via getitem
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)  # Could happen for user-defined slot attributes that were never initialized

    def get(self, key, default=None):
        """
        Returns a value of a field with the given key, or the provided default if no such field exists
        or a required field is missing value.
        """
        if key not in self.__gettable__:
            return default
        value = getattr(self, key, Missing)
        return value if value is not Missing else default

    def __eq__(self, other: Model):
        if type(self) != type(other):
            return False
        for name, primitive_name, convert, copy_value in self.__input_fields__:
            if getattr(self, name) != getattr(other, name):
                return False
        return True

    def __repr__(self):
        parts = []
        for field in self.__fields__:
            base = f'{field.name}='
            if field.serializable is not None:
                continue
            value = getattr(self, field.name)
            if field.type is list or field.type is dict:
                if value:
                    if field.type is list:
                        parts.append(f'{base}[({len(value)} items)]')
                    else:
                        parts.append(f'{base}{{({len(value)} items)}}')
                else:
                    parts.append(f'{base}{value!r}')
            elif field.type is not NotImplemented and issubclass(field.type, Model):
                parts.append(f'{base}{type(value).__name__ if isinstance(value, Model) else value}')
            else:
                parts.append(f'{base}{repr(value)}')
        return f'<{self.__class__.__name__} {{' + ', '.join(parts) + '}>'

    def items(self) -> Iterable[Tuple[str, Any]]:
        """Provides an iterator over the fields of this model, with field name and converted value pairs."""
        for name, primitive_name, convert, copy_value in self.__input_fields__:
            value = getattr(self, name)
            if value is Missing:
                continue  # Missing required fields are skipped intentionally
            yield name, value

    def copy(self, deep: bool = False) -> Model:
        """Creates an optionally deep copy of this model."""
        copied = self.__new__(self.__class__)
        for name, primitive_name, convert, copy_value in self.__input_fields__:
            value = getattr(self, name)
            if deep and copy_value is not None:
                value = copy_value(value)
            setattr(copied, name, value)
        return copied

    @classmethod
    def fields_for_role(cls, role: Role = DEFAULT_ROLE) -> List[Field]:
        """
        Lists fields present in output for a given role. Omits those suppressed by roles or None `primitive_name`.

        :param role: The :class:`Role` that controls which fields are present
        """
        if cls.__role_fields__ is NotImplemented:
            cls.__initialize_model__()
        if role.code < len(cls.__role_fields__):
            return [field for field, _, _, _, _, _, _, _ in cls.__role_fields__[role.code]]
        else:
            return [] if role.empty_by_default else list(cls.__fields__)

    @classmethod
    def field_names_for_role(cls, role: Role = DEFAULT_ROLE) -> List[str]:
        """
        Lists the field names (using primitive names, as in serialized data) present for a given role.

        :param role: The :class:`Role` that controls which fields are present
        """
        return [field.to_primitive_name for field in cls.fields_for_role(role)]


_NativeValidator = Callable[[Any, ValidationContextType], Iterable[PathErrorType]]
_ValidatorMethod = Callable[[Model, Any, ValidationContextType], None]
_SerializableFn = Callable[[Model], Any]
_ToPrimitive = Callable[[Any, Role, Any], Any]

# These rather ugly tuples measurably improve performance compared to accessing field attributes
_InputFieldConfig = Tuple[
    str,  # name
    Optional[str],  # primitive_name - if None, the field may not be filled from input data
    Callable[[Any], Any],  # convert - turn data into the field's native representation
    Optional[Callable[[Any], Any]],  # copy_value - if None, the field is atomic and doesn't need copying
]
_ValidatedFieldConfig = Tuple[
    str,  # name
    str,  # input_name - used in error message, has fallback to name if primitive names are None
    bool,  # allow_none
    Optional[_NativeValidator],  # Field's validate method
    Optional[_ValidatorMethod],  # Model's validator_method bound to a Field
]
_OutputFieldConfig = Tuple[
    Field,
    str,  # name
    Optional[_SerializableFn],  # serializable - if provided, value of the field is extracted by calling this
    Optional[_ToPrimitive],  # to_primitive - if provided, should be called to convert native value to primitive
    Optional[str],  # to_primitive_name - key used for output; in practice, this tuple isn't used if None
    bool,  # hide_none
    bool,  # hide_empty - if True, don't add the key if the value equals empty_value
    Any,  # empty_value
]
