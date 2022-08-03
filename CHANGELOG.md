# Changelog

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
