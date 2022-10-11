# stereotype

[![readthedocs.org](https://readthedocs.org/projects/stereotype/badge/?version=latest)](https://stereotype.readthedocs.io/en/latest/)
[![codecov.io](https://codecov.io/github/petee-d/stereotype/coverage.svg?branch=master)](https://codecov.io/github/petee-d/stereotype)

Stereotype is a performance-focused Python 3.8+ library for providing a structure for your data and validating it.
The models allow fast & easy conversion between primitive data and well-typed Python classes.

Stereotype is heavily influenced by the beauty of [dataclasses](https://docs.python.org/3/library/dataclasses.html)
and versatility of [Schematics](https://schematics.readthedocs.io/), while having much better performance - both in
terms of CPU usage and memory footprint. While it wasn't an influence, it is somewhat similar to
[Pydantic](https://pydantic-docs.helpmanual.io/), but also beats it in benchmarks and provides easier validation.

Stereotype supports Python 3.8 and above (future support for older versions of Python is highly unlikely) and
has 100% test coverage.

## Features
- Fields
  - All JSON atomic types - `bool`, `int`, `float`, `str`, `Optional[*]`
  - Compound fields - `List[*]` of any type or a `Dict[*, *]` of atomic types to any type
  - Model nesting - `Model` subclass fields, including recursive definitions
  - Dynamic model fields - `Model` subclass fields resolved using a string `type` key
  - Free-form fields using `Any`
  - Calculated `serializable` fields - a `property` present also in serialized data
  - Schematics compatibility field, custom fields can be defined
- Validation
  - Basic built-in validation helpers for most fields
  - Custom field validator callbacks
  - Custom `Model` instance validation methods
  - Validation separate from conversion, multiple validation errors reported with paths
- Conversion & serialization
  - Optional field defaults using atomic values or callables
  - Renaming or disabling fields for purposes of input/output/both
  - Optional hiding of `None` values from output
  - Serialization roles using field blacklists or whitelists, with inheritance or overriding


<!--- Update docs/index.rst end-line if this line moves! -->


## Documentation
[**Full documentation of stereotype**](https://stereotype.readthedocs.io/en/latest/)

### Brief usage example
```python
from typing import Optional, List
from stereotype import Model, StrField, FloatField


class Movie(Model):
    name: str
    genre: str = StrField(choices=("Comedy", "Action", "Family", "Drama"))
    ratings: Optional[float] = FloatField(min_value=1, max_value=10, default=None)
    cast: List[CastMember] = []


class CastMember(Model):
    name: str


movie = Movie({"name": "Monty Python and the Holy Grail", "genre": "Comedy", "ratings": 8.2})
movie.validate()
movie.cast.append(CastMember({"name": "John Cleese"}))
print(movie.serialize())
```

See the [Tutorial](https://stereotype.readthedocs.io/en/latest/tutorial.html)
for more examples with detailed explanations.

## Issues & contributing
Please see the [Contribution guide](https://github.com/petee-d/stereotype/blob/master/CONTRIBUTING.md)
