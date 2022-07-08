from typing import Type, Set
from unittest import TestCase

from stereotype import Model, Role, ConfigurationError, DEFAULT_ROLE, IntField

ROLE_A = Role('a')
ROLE_B = Role('b', empty_by_default=True)
ROLE_C = Role('c')
ROLE_UNKNOWN_ALL = Role('unknown_1')
ROLE_ALL = Role('all')
ROLE_NONE = Role('none', empty_by_default=True)
ROLE_UNKNOWN_NONE = Role('unknown_2', empty_by_default=True)


class MyRoles(Model):
    a1: int = 1
    b1: float = 1.1
    a2: int = IntField(to_primitive_name='a_2', default=2)
    c1: str
    b2: float = 2.2
    hidden: int = IntField(to_primitive_name=None, default=404)

    @classmethod
    def declare_roles(cls):
        yield ROLE_A.whitelist(cls.a1, cls.a2)
        yield ROLE_B.blacklist(cls.a1, cls.a2, cls.c1)
        yield ROLE_C.whitelist(cls.c1)
        yield ROLE_ALL.blacklist()
        yield ROLE_NONE.whitelist()


class TestModels(TestCase):
    def test_roles_direct(self):
        model = MyRoles({'c1': '1'})
        self._assert_my_roles(model)

    def test_role_inheritance_simple(self):
        class MyChildRoles(MyRoles):
            pass

        self.assertEqual(['a1', 'b1', 'a_2', 'c1', 'b2'], MyChildRoles.field_names_for_role(DEFAULT_ROLE))

        model = MyChildRoles({'c1': 1})
        self._assert_my_roles(model)

        self.assertEqual(['a1', 'a_2'], MyChildRoles.field_names_for_role(ROLE_A))
        self.assertEqual(['b1', 'b2'], model.field_names_for_role(ROLE_B))
        self.assertEqual(['a1', 'b1', 'a_2', 'c1', 'b2'], MyChildRoles.field_names_for_role(ROLE_UNKNOWN_ALL))
        self.assertEqual([], MyChildRoles.field_names_for_role(ROLE_UNKNOWN_NONE))

    def _assert_my_roles(self, model: Model):
        all_serialized = {'a1': 1, 'a_2': 2, 'b1': 1.1, 'b2': 2.2, 'c1': '1'}
        self.assertEqual(all_serialized, model.serialize(role=DEFAULT_ROLE))
        self.assertEqual({'a1': 1, 'a_2': 2}, model.serialize(role=ROLE_A))
        self.assertEqual({'b1': 1.1, 'b2': 2.2}, model.serialize(role=ROLE_B))
        self.assertEqual({'c1': '1'}, model.to_primitive(role=ROLE_C))
        self.assertEqual(all_serialized, model.serialize(role=ROLE_UNKNOWN_ALL))
        self.assertEqual(all_serialized, model.serialize(role=ROLE_ALL))
        self.assertEqual({}, model.serialize(role=ROLE_NONE))
        self.assertEqual({}, model.serialize(role=ROLE_UNKNOWN_NONE))

    def test_role_inheritance(self):
        class MyOtherBase(Model):
            __abstract__ = True

            a3: int = 3

        class MyChildRoles(MyRoles, MyOtherBase):
            a4: int = 4
            b3: float = 3.3

            @classmethod
            def declare_roles(cls):
                yield ROLE_A.whitelist(cls.a4)
                yield ROLE_B.blacklist(cls.a3, cls.a4)

        model = MyChildRoles({'c1': 1})
        all_serialized = {'a1': 1, 'a_2': 2, 'b1': 1.1, 'b2': 2.2, 'c1': '1', 'a3': 3, 'a4': 4, 'b3': 3.3}
        self.assertEqual(all_serialized, model.serialize())
        self.assertEqual({'a1': 1, 'a_2': 2, 'a3': 3, 'a4': 4}, model.serialize(role=ROLE_A))
        self.assertEqual({'b1': 1.1, 'b2': 2.2, 'b3': 3.3}, model.serialize(role=ROLE_B))
        self.assertEqual({'a3': 3, 'a4': 4, 'b3': 3.3, 'c1': '1'}, model.serialize(role=ROLE_C))
        self.assertEqual(all_serialized, model.serialize(role=ROLE_UNKNOWN_ALL))
        self.assertEqual(all_serialized, model.serialize(role=ROLE_ALL))
        self.assertEqual({}, model.serialize(role=ROLE_NONE))
        self.assertEqual({}, model.serialize(role=ROLE_UNKNOWN_NONE))
        self.assertEqual("<MyChildRoles {a3=3, a1=1, b1=1.1, a2=2, c1='1', b2=2.2, hidden=404, a4=4, b3=3.3}>",
                         repr(model))

        # Abstract models can still be used if necessary, but don't have the __slots__ optimization, so it's not wise
        other = MyOtherBase({'a3': 3.0})
        self.assertEqual({'a3': 3}, other.serialize())
        self.assertEqual({'a3': 3}, other.serialize(role=ROLE_A))
        self.assertEqual({}, other.serialize(role=ROLE_B))
        self.assertEqual({'a3': 3}, other.serialize(role=ROLE_C))
        self.assertEqual({'a3': 3}, other.serialize(role=ROLE_UNKNOWN_ALL))
        self.assertEqual({'a3': 3}, other.serialize(role=ROLE_ALL))
        self.assertEqual({}, other.serialize(role=ROLE_NONE))
        self.assertEqual({}, other.serialize(role=ROLE_UNKNOWN_NONE))

    def test_role_inheritance_with_override(self):
        class MyChildRoles(MyRoles):
            a3: int = 3
            b3: float = 3.3

            @classmethod
            def declare_roles(cls):
                yield ROLE_A.whitelist(cls.a2, cls.a3, override_parents=True)
                yield ROLE_B.blacklist(cls.a1, cls.a3, override_parents=True)
                yield ROLE_C.whitelist(cls.c1, override_parents=True)
                yield ROLE_ALL.whitelist(override_parents=True)
                yield ROLE_NONE.blacklist(override_parents=True)

        model = MyChildRoles({'c1': 1})
        all_serialized = {'a1': 1, 'a_2': 2, 'a3': 3, 'b1': 1.1, 'b2': 2.2, 'b3': 3.3, 'c1': '1'}
        self.assertEqual(all_serialized, model.serialize())
        self.assertEqual({'a_2': 2, 'a3': 3}, model.serialize(role=ROLE_A))
        self.assertEqual({'a_2': 2, 'b1': 1.1, 'b2': 2.2, 'b3': 3.3, 'c1': '1'}, model.serialize(role=ROLE_B))
        self.assertEqual({'c1': '1'}, model.serialize(role=ROLE_C))
        self.assertEqual(all_serialized, model.serialize(role=ROLE_UNKNOWN_ALL))
        self.assertEqual({}, model.serialize(role=ROLE_ALL))
        self.assertEqual(all_serialized, model.serialize(role=ROLE_NONE))
        self.assertEqual({}, model.serialize(role=ROLE_UNKNOWN_NONE))

    def test_nested_model_roles(self):
        class ChildA(Model):
            a: str = 'default'

            @classmethod
            def declare_roles(cls):
                yield ROLE_C.blacklist(cls.a)

        class ChildB(ChildA):
            b: int = 7

            @classmethod
            def declare_roles(cls):
                yield ROLE_B.whitelist(cls.b)

        class Parent(Model):
            a: ChildA = ChildA
            b: ChildB = ChildB

            @classmethod
            def declare_roles(cls):
                yield ROLE_B.blacklist(cls.a)

            @classmethod
            def resolve_extra_types(cls) -> Set[Type[Model]]:
                return {ChildA, ChildB}

        model = Parent()
        self.assertEqual({'a': {'a': 'default'}, 'b': {'a': 'default', 'b': 7}}, model.serialize())
        self.assertEqual({'a': {'a': 'default'}, 'b': {'a': 'default', 'b': 7}}, model.serialize(role=ROLE_A))
        self.assertEqual({'b': {'b': 7}}, model.serialize(role=ROLE_B))
        self.assertEqual({'a': {}, 'b': {'b': 7}}, model.serialize(role=ROLE_C))
        self.assertEqual({'a': {'a': 'default'}, 'b': {'a': 'default', 'b': 7}}, model.serialize(role=ROLE_ALL))
        self.assertEqual({}, model.serialize(role=ROLE_NONE))

    def test_role_configuration_error_conflict(self):
        class BadRoles(Model):
            whatever: int = 0

            @classmethod
            def declare_roles(cls):
                yield ROLE_A.whitelist(cls.whatever)
                yield ROLE_B.blacklist(cls.whatever)
                yield ROLE_A.whitelist()

        with self.assertRaises(ConfigurationError) as ctx:
            BadRoles({'whatever': 1})
        self.assertEqual('Role a configured for BadRoles multiple times', str(ctx.exception))

    def test_role_configuration_error_bad_field(self):
        class BadRoles(Model):
            not_a_field: int = 0

            @classmethod
            def declare_roles(cls):
                yield ROLE_A.whitelist('not_a_field')

        with self.assertRaises(ConfigurationError) as ctx:
            BadRoles({'not_a_field': 1})
        self.assertEqual("Role blacklist/whitelist needs member descriptors (e.g. cls.my_field), got 'not_a_field'",
                         str(ctx.exception))

    def test_role_repr(self):
        self.assertEqual('<Role default, empty_by_default=False, code=0>', repr(DEFAULT_ROLE))
        self.assertEqual('<Role a, empty_by_default=False, code=1>', repr(ROLE_A))
        self.assertEqual('<Role b, empty_by_default=True, code=2>', repr(ROLE_B))
