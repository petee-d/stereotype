Tutorial
========

--------------------
Defining flat models
--------------------

Here is a simple flat model defined using stereotype:

.. literalinclude:: ../examples/atomic_fields.py
    :language: python
    :lines: 3-17

* All models need to inherit from the :ref:`Model` class (directly or indirectly).
* All public class attributes that have a type annotation (i.e. the attribute name is followed with a colon) will be
  converted to model fields, i.e. they can be deserialized from input, serialized to output or be validated.
  See :ref:`Fields` for information about what types are supported.
* Fields the type of which is ``Optional`` (a.k.a. ``Union[None, other]``) will be valid even if ``None`` is supplied.
* The assigned value for a field will be used as the default if the key was not present in the input.
  Note ``None`` in the input will not be converted to the default.
  The default must be a value of the field's allowed type.
* If a callable is provided as a default, it will be called with no arguments to create a new default.
* If the assigned value is a stereotype ``***Field``, it can be used to configure more options than the type and default -
  like some basic validation rules, hiding ``None`` from output, overriding serialization & deserialization names, etc.
* Fields that don't provide a default (either as the field's assigned value, or using the ``default`` kwarg to a custom
  field) will be required.
* Attributes without a type annotation will not be treated as fields and are just static class members.
* Instance methods of a model can use the values freely. Note they may be called even if the model doesn't pass the
  validation rules.

----------------------------
Working with model instances
----------------------------

Model instances are created by passing dictionaries. They can then be validated and serialized back to raw data:

.. literalinclude:: ../examples/atomic_fields.py
    :language: python
    :lines: 20-30

* Some amount of conversion will be done automatically - ints to floats, floats without decimals to ints,
  strings to numbers and booleans, anything to strings.
* Calls to :func:`stereotype.Model.validate` will pass without an exception if there is no problem.
* Fields can be freely accessed as attributes to retrieve their values, class attributes and all methods work normally.
* Fields can also be assigned to. Validation can be repeated after changing a model's initial values.
* Data can be serialized back to primitive structures using :func:`stereotype.Model.to_primitive`
  or it's alias :func:`stereotype.Model.serialize`.

Validation & conversion errors
------------------------------

Validation errors raised from the :func:`stereotype.Model.validate` method can report common data issues,
such as missing required fields and broken validation rules:

.. literalinclude:: ../examples/atomic_fields.py
    :language: python
    :lines: 33-47

* The string representation of a :class:`stereotype.ValidationError` reports the first errors,
  while the ``errors`` property can be used to identify all errors in the model structure, including nested models.
* Not providing a value to a required field will trigger a validation error for the field. The model's attribute can
  still be accessed but will contain the special :data:`stereotype.Missing` object.
* Providing ``None`` to a field with a default will override the default.
  Unless the field is ``Optional``, this also causes a validation error.
* There are a few built-in validation rules for the specific types of :ref:`Fields`.
  Custom validation can be implemented using validator methods.
* Omitted required fields in the input will be missing in serialized data as well.


Conversion errors are raised during model initialization if the input to a model wasn't a dictionary or any of
    the fields contain data that cannot be interpreted by the corresponding field.

.. literalinclude:: ../examples/atomic_fields.py
    :language: python
    :lines: 50-53

* :class:`stereotype.ConversionError` also has the ``errors`` property with the same structure of errors,
  but will only have one error.

---------------------
Compound value fields
---------------------

Fields can also be lists and dictionaries of other fields:

.. literalinclude:: ../examples/compound_fields.py
    :language: python
    :lines: 3-24

* Lists are created using the ``List`` type annotation and any other supported annotation, including other lists.
* You can specify validation rules by providing an explicit :class:`stereotype.ListField`, but this is not necessary.
  Validation rules for items may be specified by providing an explicit field instance in the ``item_field`` argument.
* Dictionaries are created using the ``Dict`` type annotation, with an atomic key type and any value type.
* Extra options can again be specified with an explicit :class:`stereotype.DictField`,
  such as validation rules for the keys and values.
* You can use the ``list`` and ``dict`` constructors as defaults if the fields are not required. ``[]`` and ``{}`` used
  as defaults are supported as special cases for convenience and will be replaced with their respective constructor.

.. literalinclude:: ../examples/compound_fields.py
    :language: python
    :lines: 27-40

* Validation errors in compound fields will be located using nested dictionaries to the individual items.

-----------------
Nested structures
-----------------

Models can be used as model fields themselves.

.. literalinclude:: ../examples/compound_fields.py
    :language: python
    :lines: 3-26

* Simply use the model's identifier in the annotation.
* Model fields can also be ``Optional`` and can have a callable default, such as the model class itself.
* Add ``from __future__ import annotations`` to have fields with models that weren't declared yet.
* Note ``Any`` can be used to contain values of any type that won't be further processed.
* Note ``IsEqual.type`` doesn't have a type annotation, hence isn't a field and won't be present in serialized data.

Dynamic model fields
--------------------

The non-field string ``type`` attribute has a special usage when using dynamic model fields:

.. literalinclude:: ../examples/model_fields.py
    :language: python
    :lines: 29-51

* A ``Union`` can be used in a field type annotation only with models that have a non-annotated string ``type`` attribute.
* The ``type`` attribute values of models used together in any ``Union`` may not conflict.
* Primitive data dictionaries must have a ``type`` key with one of the ``type`` attributes in the ``Union``.
* Models can be copied using the ``copy`` method. Shallow by default, deep if requested.
* You can use already converted models in the input data (see ``equality_copy``). Those will not be copied implicitly.
