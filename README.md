# stereotype

[![codecov.io](https://codecov.io/github/petee-d/stereotype/coverage.svg?branch=master)](https://codecov.io/github/petee-d/stereotype)

Stereotype is a performance-focused Python 3.8 library for providing a structure for your data and validating it.
The models allow fast & easy conversion between primitive data and well-typed Python classes.

Stereotype is heavily influenced by the beauty of [dataclasses](https://docs.python.org/3/library/dataclasses.html)
and versatility of [Schematics](https://schematics.readthedocs.io/), while having much better performance - both in
terms of CPU usage and memory footprint. While it wasn't an influence, it is somewhat similar to
[Pydantic](https://pydantic-docs.helpmanual.io/), but also beats it in benchmarks and provides easier validation.

Stereotype supports Python 3.8 and above (future support for older versions of Python is highly unlikely) and
has 100% test coverage.

## Features
- Support for atomic fields - `bool`, `int`, `float`, `str`
- `Optional` for any supported type
- Fields with `List`s of any supported type and `Dict`s of atomic types to any supported type
- Support for `Model` subclass fields, including recursive definitions
- Dynamic model fields resolved using a string `type` key
- Free-form fields using `Any`
- Calculated `serializable` fields - a `property` present also in serialized data
- Optional field defaults using atomic values or callables
- Renaming or disabling fields for purposes of input/output/both
- Optional hiding of `None` values from output
- Some built-in validation helpers for most fields
- Custom validation instance methods with context
- Serialization roles using field blacklists or whitelists, with inheritance or overriding
- Schematics compatibility field


# Tutorial

## Atomic value fields

Here is a simple flat model defined using stereotype:
```python
from typing import Optional

from stereotype import Model, FloatField, ValidationError, Missing


class Employee(Model):
    name: str
    department: str = 'Engineering'
    female: Optional[bool] = None
    salary: float = FloatField(min_value=42., default=42.)

    human = True

    def greeting(self) -> str:
        title = {True: "Ms. ", False: "Mr. "}.get(self.female, "")
        return f'Dear {title}{self.name}'
```
* All models need to inherit from the `Model` class (directly or indirectly).
* All class attributes that have a type annotation (i.e. the attribute name is followed with a colon) will be converted
    to model fields, i.e. they can be deserialized from input, serialized to output or be validated.
    See [Fields] for information about what types are supported.
* Fields the type of which is `Optional` (a.k.a. `Union[None, other]`) will be valid even if `None` is supplied.
* The assigned value for a field will be used as the default if the key was not present in the input. Note `None` in the
    input will not be converted to the default. The default must be a value of the field's allowed type.
* If a callable is provided as a default, it will be called with no arguments to create a new default.
* If the assigned value is a stereotype `***Field`, it can be used to configure more options than the type and default -
    like some basic validation rules, hiding `None` from output, overriding serialization & deserialization names, etc.
* Fields that don't provide a default (either as the field's assigned value, or using the `default` kwarg to a custom
    field) will be required.
* Attributes without a type annotation will not be treated as fields and are just static class members.
* Instance methods of a model can use the values freely. Note they may be called even if the model doesn't pass the
    validation rules.

Model instances are created by passing dictionaries. Models can then be validated and serialized back to raw data:
```python
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
```python
model = Employee({'department': None, 'salary': '10'})
try:
    model.validate()
    assert False, 'Validation fails due to errors below'  # pragma: no cover
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
assert model.to_primitive() == {'department': None, 'female': None, 'salary': 10.0}
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
```python
try:
    model = Employee({'name': 'Alien', 'female': 'Unknown'})
except ConversionError as e:
    assert str(e) == 'female: Value must be a boolean or a true/false/yes/no string value'
```
* `ConversionError`s also have the `errors` property with the same structure of errors, but will only have one error.

## Compound value fields

Fields can also be lists and dictionaries of other fields:
```python
from typing import List, Dict

from stereotype import Model, ListField, StrField, FloatField, ValidationError
from stereotype.fields.compound import DictField


class Book(Model):
    name: str
    authors: List[str] = ListField(min_length=1)
    reviews: Dict[str, float] = DictField(
        key_field=StrField(min_length=1),
        value_field=FloatField(min_value=0, max_value=5),
        default=dict,
    )


model = Book({'name': 'The Go Programming Language'})
model.authors = ['Alan A.A. Donovan', 'Brian W. Kernighan']
model.validate()
assert model.to_primitive() == {
    'name': 'The Go Programming Language',
    'authors': ['Alan A.A. Donovan', 'Brian W. Kernighan'],
    'reviews': {},
}
```
* Lists are created using the `List` type annotation and any other supported annotation, including other lists.
* You can specify validation rules by providing an explicit `ListField`, but this is not necessary.
    Validation rules for items may be specified by providing an explicit field instance in the `item_field` argument.
* Dictionaries are created using the `Dict` type annotation, with an atomic key type and any value type.
* Extra options can again be specified with an explicit `DictField`, such as validation rules for the keys and values.
* You can use the `list` and `dict` constructors as defaults if the fields are not required.

```python
model = Book({
    'name': "The Hitchhiker's Guide to the Galaxy",
    'authors': ['Douglas Adams', None],
    'reviews': {'dolphins': 4.2, 'whales': -2},
})
assert model.reviews['dolphins'] == 4.2
try:
    model.validate()
    assert False, 'Validation fails due to errors below'  # pragma: no cover
except ValidationError as e:
    assert e.errors == {
        'authors': {'1': ['This field is required']},
        'reviews': {'whales': ['Must be between 0 and 5']},
    }
```
* Validation errors in compound fields will be located using nested dictionaries to the individual items.


## Deeper structures with model fields

Models can be used as model fields themselves.
```python
from __future__ import annotations
from typing import Optional, Any, Union, List
from stereotype import Model


class Variable(Model):
    name: str


class IsEqual(Model):
    type = 'equal'

    variable: Variable
    constant: Constant


class Constant(Model):
    value: Optional[Any] = None


equality = IsEqual({'variable': {'name': 'x'}, 'constant': {'value': 42}})
assert equality.variable.name == 'x'
assert equality.type == 'equal'
assert equality.to_primitive() == {'variable': {'name': 'x'}, 'constant': {'value': 42}}
```
* Simply use the model's identifier in the annotation.
* Model fields can also be `Optional` and can have a callable default, such as the model class itself.
* Add `from __future__ import annotations` to have fields with models that weren't declared yet.
* Note `Any` can be used to contain values of any type that won't be further processed.
* Note `IsEqual.type` doesn't have a type annotation, hence isn't a field and won't be present in serialized data.

The non-field string `type` attribute has a special usage when using dynamic model fields:
```python
class Negation(Model):
    type = 'not'

    formula: Union[IsEqual, Conjunction]


class Conjunction(Model):
    type = 'and'

    operands: List[Union[IsEqual, Negation, Conjunction]] = list


equality_copy = equality.copy(deep=True)
model = Conjunction({'operands': [
    {'type': 'not', 'formula': equality_copy},
    {'type': 'equal', 'variable': {'name': 'y'}, 'constant': {}},
]})
assert isinstance(model.operands[0], Negation)
assert model.operands[0].type == 'not'
assert model.to_primitive() == {'operands': [
    {'type': 'not', 'formula': {'type': 'equal', 'variable': {'name': 'x'}, 'constant': {'value': 42}}},
    {'type': 'equal', 'variable': {'name': 'y'}, 'constant': {'value': None}},
]}
```
* A `Union` can be used in a field type annotation only with models that have a non-annotated string `type` attribute.
* The `type` attribute values of models used together in any `Union` may not conflict.
* Primitive data dictionaries must have a `type` key with one of the `type` attributes in the `Union`.
* Models can be copied using the `copy` method. Shallow by default, deep if requested.
* You can use already converted models in the input data (see `equality_copy`). Those will not be copied implicitly.
