from __future__ import annotations

import sys
from typing import Set, Type, Union
from unittest import TestCase, skip

from stereotype import Model, DictField, IntField, ValidationError, DynamicModelField

if tuple(sys.version_info[:2]) < (3, 10):
    skip_if_not_python3_10 = skip('This test suite only works in Python 3.10 and above')
else:
    def skip_if_not_python3_10(cls):
        return cls


@skip_if_not_python3_10
class TestPython310Annotations(TestCase):
    def test_optional(self):
        class Optional(Model):
            opt: int | None = 1

        model = Optional({'opt': None})
        model.validate()
        self.assertEqual({'opt': None}, model.to_primitive())

    def test_list_dict(self):
        class Collections(Model):
            list: list[int] = []
            dict: dict[str, int] = DictField(value_field=IntField(max_value=5))

        model = Collections({'list': ['1', 2.0], 'dict': {}})
        model.validate()
        self.assertEqual({'list': [1, 2], 'dict': {}}, model.to_primitive())

        model = Collections({'dict': {'1': 1, 3: '3', '6': 6}})
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual({'dict': {'6': ['Must be at most 5']}}, ctx.exception.errors)
        self.assertEqual({'list': [], 'dict': {'1': 1, '3': 3, '6': 6}}, model.to_primitive())

    def test_union(self):
        class A(Model):
            type = 'a'
            a: int = 1

        class B(Model):
            type = 'b'
            b: int = 2

        class Unionized(Model):
            old: Union[A, B] = A
            simple: A | B
            advanced: A | B = DynamicModelField(default=A, primitive_name='other')

            @classmethod
            def resolve_extra_types(cls) -> Set[Type[Model]]:
                return {A, B}

        model = Unionized({'simple': {'type': 'b'}})
        model.validate()
        self.assertEqual({
            'old': {'type': 'a', 'a': 1},
            'simple': {'type': 'b', 'b': 2},
            'other': {'type': 'a', 'a': 1},
        }, model.to_primitive())
