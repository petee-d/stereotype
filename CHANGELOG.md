# Changelog

## v1.4.2
Fixes:
* Fixed being unable to inherit from non-Model classes
* Fixed inheritance of abstract Models from non-abstract Models
* Fixed support of new Union (`|`) and `list` & `dict` annotations in Python 3.10 and above

## v1.4.1
Features:
* Model attributes with `ClassVar` won't be interpreted as fields, like in dataclasses

Fixes:
* Fixed being unable to declare roles for abstract models

## v1.4.0
Features:
* Added `Model.fields_for_role` class method for inspecting `Field` objects usually displayed by a role

Changes:
* Added external documentation using sphinx, simplified README.md
* Added contribution guideline, Makefile and other developer experience improvements
* Started raising `ConfigurationError` if a `Model` attribute is an explicit `Field` but lacks a type annotation

## v1.3.1
Fixes:
* Fixed `Missing` behavior with `deepcopy`

## v1.3.0
Features:
* Added support for passing opaque `context` when calling `to_primitive` on models and fields

Fixes:
* Fixed field validator callbacks not working for `Optional` fields with a default value
* Renamed `tests.compat` package to `tests.contrib` to reflect the name change in v1.2.0

## v1.2.0
Features:
* Added support for field validator callbacks
* Added support for regex validation in `StrField`
* Added support for empty lists and dicts as defaults in `ListField` and `DictField`
* Added most missing docstrings

Changes:
* Renamed `compat` package to `contrib`

## v1.1.0
Features:
* Enabled using Schematics models as fields via `SchematicsModelField` - see
  [here](https://github.com/petee-d/stereotype/tree/master/stereotype/contrib#schematics)
* Added `hide_empty` support to `ModelField`, allowing to omit models serialized as empty dicts

Changes:
* Improved resolving annotations to fields, making it more flexible and improving error reporting
* Support wrapping properties with the `serializable` decorator - allows better type checking

Fixes:
* Fixed `field_names_for_role` not using `to_primitive_name` and not working before `Model` is initialized
* Fix roles not being propagated when serializing nested models
* Fix `ConversionError` not tracking path through `ListField` or `DictField`

## v1.0.0
Initial release
