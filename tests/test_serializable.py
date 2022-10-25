from __future__ import annotations

import math
from typing import Optional, Iterable
from unittest import TestCase

from stereotype import Model, serializable, Role, RequestedRoleFields, IntField

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
    @property
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
        class Abstract(Model):
            __abstract__ = True

            normal: str = "normal"

            @serializable(to_primitive_name="abnormal")
            def weird(self):
                return f"not {self.normal}"

            @classmethod
            def declare_roles(cls) -> Iterable[RequestedRoleFields]:
                yield role_a.blacklist(cls.normal)
                yield role_b.blacklist(cls.normal, cls.weird)

        class ChildModel(MyModel, Abstract):
            @serializable
            def a_plus_b(self) -> int:
                return self.a * self.b

            @serializable
            def real_a_plus_b(self) -> int:
                return self.a + self.b

            @property
            def fake_field(self):
                return 42

            @classmethod
            def declare_roles(cls) -> Iterable[RequestedRoleFields]:
                yield role_b.blacklist(cls.real_a_plus_b)

        ChildModel.fake_field.fget.__field__ = IntField(default=47)

        model = ChildModel({'a': 12, 'b': -5})
        self.assertEqual(12, model.a)
        self.assertEqual(-5, model.b)
        self.assertEqual(-60, model.a_plus_b)
        self.assertEqual(7, model.real_a_plus_b)
        self.assertEqual('B', model.lower_key)
        self.assertEqual(42, model.fake_field)
        self.assertEqual("normal", model.normal)
        self.assertEqual("not normal", model.weird)
        self.assertAlmostEqual(13.0, model.pythagoras, 3)
        self.assertEqual({
            'a': 12,
            'b': -5,
            'a_plus_b': -60,
            'lower_key': 'B',
            'c': 13.0,
            'real_a_plus_b': 7,
            'normal': 'normal',
            'abnormal': 'not normal',
        }, model.serialize())
        self.assertEqual({
            'a': 12,
            'a_plus_b': -60,
            'lower_key': 'B',
            'real_a_plus_b': 7,
            'abnormal': 'not normal',
        }, model.serialize(role_a))
        self.assertEqual({
            'lower_key': 'B',
            'a_plus_b': -60,
        }, model.serialize(role_b))
        model.validate()

    def test_serializable_override(self):
        class First(Model):
            overridden_attribute: int
            inherited_attribute: int

            @serializable
            def overridden_serializable(self) -> int:
                return -self.overridden_attribute

            @serializable
            def inherited_serializable(self) -> int:
                return -self.inherited_attribute

        class Second(First):
            overridden_serializable: int

            @serializable
            def overridden_attribute(self) -> int:
                return -self.overridden_serializable

        class Abstract(First):
            __abstract__ = True
            overridden_serializable: str

            @serializable
            def overridden_attribute(self) -> str:
                return str(self.overridden_serializable)

        class Third(Abstract):
            pass

        model = First({'overridden_attribute': 1, 'inherited_attribute': 2})
        self.assertEqual(-1, model.overridden_serializable)
        self.assertEqual(-2, model.inherited_serializable)
        self.assertEqual({'overridden_attribute': 1, 'inherited_attribute': 2,
                          'overridden_serializable': -1, 'inherited_serializable': -2}, model.serialize())

        model = Second({'overridden_attribute': 1, 'inherited_attribute': 2,
                        'overridden_serializable': 3, 'inherited_serializable': 1})
        self.assertEqual(-3, model.overridden_attribute)
        self.assertEqual(2, model.inherited_attribute)
        self.assertEqual(3, model.overridden_serializable)
        self.assertEqual(-2, model.inherited_serializable)
        self.assertEqual({'overridden_attribute': -3, 'inherited_attribute': 2,
                          'overridden_serializable': 3, 'inherited_serializable': -2}, model.serialize())

        model = Third({'overridden_attribute': 1, 'inherited_attribute': 2,
                       'overridden_serializable': 3, 'inherited_serializable': 1})
        self.assertEqual("3", model.overridden_attribute)
        self.assertEqual(2, model.inherited_attribute)
        self.assertEqual("3", model.overridden_serializable)
        self.assertEqual(-2, model.inherited_serializable)
        self.assertEqual({'overridden_attribute': "3", 'inherited_attribute': 2,
                          'overridden_serializable': "3", 'inherited_serializable': -2}, model.serialize())

    def test_items(self):
        model = MyModel({})
        self.assertEqual([], list(model.items()))
        model = MyModel({'a': 12, 'b': -5})
        self.assertEqual([('a', 12), ('b', -5)], list(model.items()))
