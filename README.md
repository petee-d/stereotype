# supermodel

Supermodel is a performance-focused Python 3.8 library for providing a structure for your data and validating it.
The models allow fast & easy conversion between primitive data and well-typed Python classes.

Supermodel is heavily influenced by the beauty of [dataclasses](https://docs.python.org/3/library/dataclasses.html)
and versatility of [Schematics](https://schematics.readthedocs.io/), while having much better performance - both in
terms of CPU usage and memory footprint. While it wasn't an influence, it is somewhat similar to
[Pydantic](https://pydantic-docs.helpmanual.io/), but also beats it in benchmarks and provides easier validation.

Supermodel supports Python 3.8 and above (future support for older versions of Python is highly unlikely) and
has 100% line test coverage.

## Features
- Support for atomic fields - `bool`, `int`, `float`, `str`
- `Optional` for any supported type
- Fields with `List`s of any supported type and `Dict`s of atomic types to any supported type
- Support for `Model` subclass fields, including recursive definitions
- Dynamic model fields resolved using a string `type` key
- Optional field defaults using atomic values or callables
- Renaming or disabling fields for purposes of input/output/both
- Optional hiding of `None` values from output
- Some built-in validation helpers for most fields
- Custom validation instance methods with context
- Serialization roles using field blacklists or whitelists, with inheritance or overriding

## TODO
- this Readme and proper documentation
- CI & PIP
- Better ConversionError localisation
- Support for ForwardRef (quoted types)
- Generating schema
- Calculated serializable fields

# Documentation

## Flat models

Here is a simple flat model defined using supermodel:
```
from typing import Optional

from supermodel import Model, FloatField


class Employee(Model):
    name: str
    department: str = 'Engineering'
    female: Optional[bool] = None
    salary: float = FloatField(min_value=42., default=42.)

    human = True

    def greeting(self) -> str:
        return f'Dear { {True: "Ms. ", False: "Mr. "}.get(self.female, "")}{self.name}'
```
* All models need to inherit from the `Model` class (directly or indirectly).
* All class attributes that have a type annotation (i.e. the attribute name is followed with a colon) will be converted
    to model fields, i.e. they can be deserialized from input, serialized to output or be validated.
    See [Fields] for information about what types are supported.
* Fields the type of which is `Optional` (a.k.a. `Union[None, other]`) will be valid even if `None` is supplied.
* The assigned value for a field will be used as the default if the key was not present in the input. Note `None` in the
    input will not be converted to the default. The default must be a value of the field's allowed type.
* If a callable is provided as a default, it will be called with no arguments to create a new default.
* If the assigned value is a supermodel `***Field`, it can be used to configure more options than the type and default -
    like some basic validation rules, hiding `None` from output, overriding serialization & deserialization names, etc.
* Fields that don't provide a default (either as the field's assigned value, or using the `default` kwarg to a custom
    field) will be required.
* Attributes without a type annotation will not be treated as fields and are just static class members.
* Instance methods of a model can use the values freely. Note they may be called even if the model doesn't pass the
    validation rules.

Model instances are created by passing dictionaries. Models can then be validated and serialized back to raw data:
```
model = Employee({'name': 'Jane Doe', 'female': True, 'salary': 150000})
model.validate()
assert model.name == 'Jane Doe'
assert model.department == 'Engineering'
assert model.female is True
assert model.salary == 150000.0
assert model.human is True
assert model.greeting() == 'Dear Ms. Jane Doe'
model.salary = 200000.0
primitive = model.to_primitive()
assert primitive == {'name': 'Jane Doe', 'department': 'Engineering', 'female': True, 'salary': 200000.0}
```
* Some amount of conversion will be done automatically - ints to floats, floats without decimals to ints,
    strings to numbers and booleans, anything to strings.
* Calls to `validate` will pass without an exception if there is no problem.
* Fields can be freely accessed as attributes to retrieve their values, class attributes and all methods work normally.
* Fields can also be assigned to. Validation can be repeated after changing a model's initial values.
* Data can be serialized back to primitive structures using `to_primitve` or it's alias `serialize`.

Validation errors raised from the `validate` method can report common data issues, such as missing required fields
    and broken validation rules:
```
from supermodel import ValidationError, Missing

model = Employee({'department': None, 'salary': '10'})
try:
    model.validate()
    assert False, 'Validation fails due to errors below'
except ValidationError as e:
    assert str(e) == 'name: This field is required'
    assert e.errors == {
        'name': ['This field is required'],
        'department': ['This field is required'],
        'salary': ['Must be at least 42.0'],
    }
assert model.name is Missing
assert model.department is None
assert model.salary == 10.0
assert model.to_primitive() == {'department': None, 'female': None, 'salary': 1.0}
```
* The string representation of a `ValidationError` reports the first errors, while the `errors` property can be used
    to identify all errors in the model structure, including nested models.
* Not providing a value to a required field will trigger a validation error for the field. The model's attribute can
    still be accessed but will contain the special `Missing` object.
* Providing `None` to a field with a default will override the default. Unless the field is `Optional`, this also causes
    a validation error.
* There are a few built-in validation rules for the specific `Field` types. Custom validation can be implemented using
    [validator methods].
* Omitted required fields in the input will be missing in serialized data as well.

Conversion errors are raised during model initialization if the input to a model wasn't a dictionary or any of
    the fields contain data that cannot be interpreted by the corresponding field.
```
from supermodel import ConversionError

try:
    model = Employee({'name': 'Alien', 'female': 'Unknown'})
except ConversionError as e:
    assert str(e) == 'female: Value must be a boolean or a true/false/yes/no string value'
```
* `ConversionError`s also have the `errors` property with the same structure of errors, but will only have one error.


## Deep structures
TODO
