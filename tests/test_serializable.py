from __future__ import annotations

import math
from typing import Optional, Iterable
from unittest import TestCase

from supermodel import Model, serializable, Role, RequestedRoleFields

role_a = Role('role_a')
role_b = Role('role_b')


class MyModel(Model):
    a: int
    b: int

    @serializable
    def a_plus_b(self) -> int:
        return self.a + self.b

    @serializable(hide_none=True)
    def lower_key(self) -> Optional[str]:
        if self.a == self.b:
            return None
        return 'A' if self.a < self.b else 'B'

    @serializable(to_primitive_name='c')
    def pythagoras(self) -> float:
        return math.sqrt(self.a * self.a + self.b * self.b)

    @property
    def a_minus_b(self) -> int:
        return self.a - self.b

    @classmethod
    def declare_roles(cls) -> Iterable[RequestedRoleFields]:
        yield role_a.blacklist(cls.b, cls.pythagoras)
        yield role_b.whitelist(cls.lower_key)


class TestSerializable(TestCase):
    def test_serializable_normal(self):
        model = MyModel({'a': 3, 'b': 4, 'a_plus_b': 'not 7'})
        self.assertEqual(3, model.a)
        self.assertEqual(4, model.b)
        self.assertEqual(7, model.a_plus_b)
        self.assertEqual('A', model.lower_key)
        self.assertEqual(5.0, model.pythagoras)
        self.assertEqual(-1, model.a_minus_b)
        self.assertEqual({'a': 3, 'b': 4, 'a_plus_b': 7, 'lower_key': 'A', 'c': 5.0}, model.serialize())
        self.assertEqual({'lower_key': 'A'}, model.serialize(role_b))
        model.validate()
        self.assertEqual('<Field pythagoras of type serializable, required, to output c>', str(MyModel.__fields__[-1]))
        self.assertEqual('<MyModel {a=3, b=4}>', repr(model))

    def test_serializable_special(self):
        model = MyModel({'a': 2, 'b': 2})
        self.assertEqual(2, model.a)
        self.assertEqual(2, model.b)
        self.assertEqual(4, model.a_plus_b)
        self.assertIsNone(model.lower_key)
        self.assertAlmostEqual(2.828, model.pythagoras, 3)
        self.assertEqual({'a': 2, 'a_plus_b': 4}, model.serialize(role_a))
        self.assertEqual({}, model.serialize(role_b))
        model.validate()

    def test_serializable_inheritance(self):
        class ChildModel(MyModel):
            @serializable
            def a_plus_b(self) -> int:
                return self.a * self.b

            @serializable
            def real_a_plus_b(self) -> int:
                return self.a + self.b

            @classmethod
            def declare_roles(cls) -> Iterable[RequestedRoleFields]:
                yield role_b.blacklist(cls.real_a_plus_b)

        model = ChildModel({'a': 12, 'b': -5})
        self.assertEqual(12, model.a)
        self.assertEqual(-5, model.b)
        self.assertEqual(-60, model.a_plus_b)
        self.assertEqual(7, model.real_a_plus_b)
        self.assertEqual('B', model.lower_key)
        self.assertAlmostEqual(13.0, model.pythagoras, 3)
        self.assertEqual({'a': 12, 'b': -5, 'a_plus_b': -60, 'lower_key': 'B', 'c': 13.0, 'real_a_plus_b': 7},
                         model.serialize())
        self.assertEqual({'a': 12, 'a_plus_b': -60, 'lower_key': 'B', 'real_a_plus_b': 7}, model.serialize(role_a))
        self.assertEqual({'lower_key': 'B', 'a_plus_b': -60}, model.serialize(role_b))
        model.validate()
