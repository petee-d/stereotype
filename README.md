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
