from typing import Type, Set, Iterable
from unittest import TestCase

from stereotype import Model, Role, ConfigurationError, DEFAULT_ROLE, IntField, StrField, serializable, \
    RequestedRoleFields
from stereotype.fields.serializable import SerializableField

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
    hidden: int = IntField(to_primitive_name=None, default=404)

    @serializable
    def b2(self) -> float:
        return self.b1 * 2

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

    def test_role_inheritance_fields_for_role(self):
        class MyChildRoles(MyRoles):
            pass

        class OtherChildRoles(MyChildRoles):
            c1: str = StrField(primitive_name=None)

        self.assertEqual(['a1', 'b1', 'a2', 'c1', 'b2'], [f.name for f in MyChildRoles.fields_for_role()])
        self.assertEqual(['a1', 'b1', 'a2', 'b2'], [f.name for f in OtherChildRoles.fields_for_role()])
        self.assertEqual(['a1', 'b1', 'a_2', 'c1', 'b2'], MyChildRoles.field_names_for_role())

        model = MyChildRoles({'c1': 1})
        self._assert_my_roles(model)

        self.assertEqual([MyChildRoles.__fields__[0], MyChildRoles.__fields__[2]], MyChildRoles.fields_for_role(ROLE_A))
        self.assertEqual(['a1', 'a_2'], MyChildRoles.field_names_for_role(ROLE_A))

        self.assertEqual(['b1', 'b2'], [f.name for f in MyChildRoles.fields_for_role(ROLE_B)])
        self.assertIsInstance(MyChildRoles.fields_for_role(ROLE_B)[1], SerializableField)
        self.assertEqual(['b1', 'b2'], model.field_names_for_role(ROLE_B))

        self.assertEqual(['a1', 'b1', 'a2', 'b2'], [f.name for f in OtherChildRoles.fields_for_role(ROLE_UNKNOWN_ALL)])
        self.assertEqual(['a1', 'b1', 'a_2', 'c1', 'b2'], MyChildRoles.field_names_for_role(ROLE_UNKNOWN_ALL))

        self.assertEqual([], MyChildRoles.field_names_for_role(ROLE_UNKNOWN_NONE))
        self.assertEqual([], OtherChildRoles.fields_for_role(ROLE_UNKNOWN_NONE))

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
        self.assertEqual("<MyChildRoles {a3=3, a1=1, b1=1.1, a2=2, c1='1', hidden=404, a4=4, b3=3.3}>", repr(model))

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

    def test_abstract_model_roles(self):
        class Abstract1(Model):
            __abstract__ = True
            x: int = 1

            @classmethod
            def declare_roles(cls) -> Iterable[RequestedRoleFields]:
                yield ROLE_A.blacklist(cls.x)

        class Abstract2(Abstract1):
            __abstract__ = True
            y: str

            @classmethod
            def declare_roles(cls) -> Iterable[RequestedRoleFields]:
                yield ROLE_B.whitelist(cls.x, cls.y)

        class Child(Abstract2):
            z: int = 3

            @classmethod
            def declare_roles(cls) -> Iterable[RequestedRoleFields]:
                yield ROLE_C.blacklist(cls.y, cls.z)
                yield ROLE_ALL.whitelist(cls.x, cls.y, cls.z)
                yield ROLE_NONE.whitelist(override_parents=True)

        child = Child({"y": "test"})
        self.assertEqual({'x': 1, 'y': 'test', 'z': 3}, child.to_primitive())
        self.assertEqual({'y': 'test', 'z': 3}, child.to_primitive(role=ROLE_A))
        self.assertEqual({'x': 1, 'y': 'test'}, child.to_primitive(role=ROLE_B))
        self.assertEqual({'x': 1}, child.to_primitive(role=ROLE_C))
        self.assertEqual({'x': 1, 'y': 'test', 'z': 3}, child.to_primitive(role=ROLE_ALL))
        self.assertEqual({}, child.to_primitive(role=ROLE_NONE))

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
        self.assertEqual('<Role default>', repr(DEFAULT_ROLE))
        self.assertEqual('<Role a>', repr(ROLE_A))
        self.assertEqual('<Role b, empty by default>', repr(ROLE_B))
