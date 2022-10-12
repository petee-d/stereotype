# Parts of this file are referenced from docs by line numbers, always update docs after changing it!

from typing import List, Dict
from stereotype import Model, ListField, StrField, FloatField, ValidationError, DictField


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


model = Book({
    'name': "The Hitchhiker's Guide to the Galaxy",
    'authors': ['Douglas Adams', None],
    'reviews': {'dolphins': 4.2, 'whales': -2},
})
assert model.reviews['dolphins'] == 4.2
try:
    model.validate()
    assert False, 'Validation fails due to the error below'  # pragma: no cover
except ValidationError as e:
    assert e.errors == {
        'authors': {'1': ['This field is required']},
        'reviews': {'whales': ['Must be between 0 and 5']},
    }
