# Compatibility & migration from other libraries

## Schematics

As stereotype was created mainly as a replacement for Schematics, it comes with very similar interfaces and the support
for using Schematics models as stereotype `Model` fields, using `SchematicsModelField`. This can be very helpful
if a big-bang migration from Schematics to stereotype within a codebase isn't be feasible.

Schematics is normally not a stereotype dependency (in fact, it has no dependencies outside the standard library),
it becomes one only if `SchematicsModelField` is used explicitly. Therefore, whenever a Schematics model is to be used
within a stereotype `Model`, annotations are not enough, `SchematicsModelField` must be imported and used.
If using roles, `Role` names must be identical to the roles used within Schematics models.

Other than that, `SchematicsModelField` functions just like a normal `ModelField`, supporting all the usual options,
and it is usable even within lists and dicts.

### SchematicsModelField example

```python
from typing import Optional, List

from schematics.models import Model as SchematicsModel
from schematics.types import StringType, IntType

from stereotype import Model, ListField
from stereotype.contrib.schematics import SchematicsModelField


class Leaf(SchematicsModel):
    color: str = StringType(required=True, default="green")


class Fruit(SchematicsModel):
    worms: Optional[int] = IntType()


class Branch(Model):
    length: float
    fruit: Optional[Fruit] = SchematicsModelField(hide_none=True, default=None)
    leaves: List[Leaf] = ListField(SchematicsModelField(), max_length=50)


branch = Branch({'length': 42, 'leaves': [{'color': 'yellow'}, {}]})
assert branch.leaves[1].color == 'green'
assert branch.fruit is None
assert branch.serialize() == {'length': 42, 'leaves': [{'color': 'yellow'}, {'color': 'green'}]}

branch.fruit = Fruit({'worms': 2})
assert branch.serialize()['fruit'] == {'worms': 2}
branch.validate()
```

### Migration cheat-sheet

This section provides a quick guide into migrating models from Schematics to stereotype,
highlighting the key differences and showing how the concepts translate.

* The first step is to change imports to import `Model` from `stereotype` instead of `schematics`
* Fields
  * Whereas **type-annotating fields** when using Schematics is just a good practice, it's **mandatory** with stereotype
  * **Explicit fields are not needed** if the Schematics field supplied only the `required` or `default` options
    * This is because stereotype usually infers the type information (incl. whether `None` is allowed) from the 
      type annotation, whereas the default can be supplied instead of the `*Field` if no other options are
      needed - see below
  * Otherwise, change the fields from Schematics `*Type` to stereotype `*Field` classes like this:
    * `typing.Any` = `BaseType()` -> `AnyField()`
      * Usable when type validation is not desired
    * `bool` = `BooleanType()` -> `BoolField()`
      * Note stereotype tries to be consistent with the type names
    * `int` = `IntType()` -> `IntField()` and `float` = `FloatType` -> `FloatField`
      * `min_value` and `max_value` validators work the same
    * `str` = `StringType` -> `StrField`
      * `min_length`, `max_length` and `choices` validators work the same
    * `typing.List[<item>]` = `ListType(<item_type>)` -> `ListField(<item_field>)`
      * Validator names are different - `min_size` -> `min_length` and `max_size` -> `max_length`
      * The inner item field may be omitted if no option other than `required` was specified for the items - 
        stereotype will infer the inner field from the annotation even recursively
    * `typing.Dict[<key>, <value>]` = `DictType(<value_type>)` -> `DictField(<key_type>, <value_type>)`
      * Validator names are different - `min_size` -> `min_length` and `max_size` -> `max_length`
  * Unlike Schematics, **stereotype fields don't allow None by default**
    * Where the Schematics model had `required=False` (the default), make the type annotation `Optional[...]`
    * If `Optional` isn't used, fields will reject `None` during validation
  * Schematics uses `None` as the default unless otherwise specified, **defaults in stereotype must be explicit**
    * If no default is specified for a stereotype field, conversion will fill in the `stereotype.Missing` placeholder
      * Validation will fail for all `Missing` fields, serialization will omit them, but they can be encountered when
        accessing attributes of model that doesn't pass validation
    * Specify a default either as the value for the field (`value: int = 42`), or as the `default` kwarg of `*Field`
      * If a callable was passed as the default, it will be called every time to create the default -
        useful for non-atomic defaults, such as empty lists or models (`model: TheModel = TheModel`)
  * Schematics type options `serialized_name` and `deserialize_from` can be replaced using the stereotype options
    `primitive_name` and `to_primitive_name` - they don't map 1:1, see their documentation
  * Schematics `serialize_when_none=False` maps to stereotype `hide_none=True`
    * Moreover, stereotype fields support options like `hide_false`, `hide_zero` and `hide_empty`, depending on the type
* Method validators
  * Schematics signature is `def validate_<field_name>(cls, data, value)`
    * `value` is the value of the field being validated and `data` contains a dictionary with the other values
    * Being actually executed as a class method, the other values cannot be accessed using `self`
  * Stereotype signature is `def validate_<field_name>(self, value, context)`
    * `value` means the same as in schematics, but `context` doesn't contain the other fields - it is any value you
      may have passed as an extra argument to the model `validate` method, allowing context-specific validation logic
      * `context` usually isn't needed and can be caught as `_`
    * Stereotype executes these as instance methods, so other fields are simply accessed using `self`
* Serialization roles
  * In Schematics, serialization roles are string constants that are used in each class relying on them like this:
    ```python
    class Options:
        roles = {
            'my_role': blacklist('my_field'),
        }
    ```
  * In stereotype, roles should be declared as global symbols in a shared package like `MY_ROLE = Role('my_role')`
    and used like this:
    ```python
    @classmethod
    def declare_roles(cls):
        yield MY_ROLE.blacklist(cls.my_field)
    ```
  * Unlike in Schematics, stereotype roles are inherited by subclasses
    (this can be overridden using `override_parents=True`)
    and roles can be used even with models that don't specify their behavior (`empty_by_default` controls the default)
  * When a `SchematicsModelField` is used, stereotype will serialize the Schematics model with the `role.name`
    of the supplied stereotype, if any (`None` is used for the `DEFAULT_ROLE`)
