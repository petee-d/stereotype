from __future__ import annotations

from copy import copy, deepcopy
from typing import Set, cast, Any, Optional, List, Dict, Union, Type, ClassVar
from unittest import TestCase

from stereotype import Model, Missing, ValidationError, ConversionError, BoolField, IntField, ConfigurationError, \
    FloatField, StrField, DataError, serializable
from stereotype.fields.base import Field, AnyField
from stereotype.fields.compound import DictField
from tests.common import Leaf


class DriedLeaf(Leaf):
    healthy = False
    crunchy: ClassVar[bool] = True
    age: float = FloatField(max_value=5, default=0.)


class PropertyAccessBase(Model):
    __slots__ = ['extra_slot']

    basic_field: str

    @serializable
    def basic_serializable(self):
        return self.basic_field

    @property
    def basic_property(self):
        return self.basic_field


class PropertyAccess(PropertyAccessBase):
    default_field: str = 'hello'

    @serializable
    def default_serializable(self):
        return self.default_field

    @property
    def default_property(self):
        return self.default_field


class NonModel:
    def __init__(self, x=1):
        self.x = x

    def __eq__(self, other):
        return self.x == other.x

    def __repr__(self):
        return f'<{self.x}>'


class TestModels(TestCase):
    def test_bad_init(self):
        with self.assertRaises(ConversionError) as ctx:
            DriedLeaf(cast(dict, 'bad'))
        self.assertEqual('Supplied type str, needs a mapping', str(ctx.exception))
        self.assertEqual({'_global': ['Supplied type str, needs a mapping']}, ctx.exception.errors)

    def test_initialized_baseclass(self):
        Leaf()  # Ensures it is pre-initialized
        model = DriedLeaf({'color': 'brown'})
        self.assertEqual('brown', model.color)
        self.assertEqual(0, model.age)
        self.assertIs(False, model.healthy)
        self.assertIs(True, model.crunchy)
        model.validate()
        self.assertEqual({'color': 'brown', 'age': 0}, model.serialize())

    def test_non_initialized_baseclass(self):
        class MyBase(Model):
            a: int
            b: float
            c: int = IntField(hide_none=True, default=-5)

        class MyChild(MyBase):
            b: str = StrField(primitive_name='bb')
            d: bool = True

            def validate_a(self, value, _):
                if value <= 0:
                    raise ValueError('Must be positive')

            def validate_b(self, value, _):
                if not value:
                    raise ValueError('Must be truthy')

            def validate_c(self, value, _):
                if value >= 0:
                    raise ValueError('Must be negative')

        class AnotherChild(MyBase):
            pass

        model = MyChild({'a': 1, 'b': 'ignored', 'bb': 'abc'})
        self.assertEqual(1, model.a)
        self.assertEqual('abc', model.b)
        self.assertEqual(-5, model.c)
        self.assertIs(True, model.d)
        model.validate()
        self.assertEqual({'a': 1, 'bb': 'abc', 'c': -5, 'd': True}, model.serialize())
        model.a = 0
        model.b = ''
        model.c = 4
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual({'a': ['Must be positive'], 'bb': ['Must be truthy'], 'c': ['Must be negative']},
                         ctx.exception.errors)

        # If explicit fields were not copied, the validator method may leak to the base class or the other subclass
        base = MyBase({'a': 0, 'b': 0, 'c': 1})
        self.assertEqual(0, base.a)
        self.assertEqual(0, base.b)
        self.assertEqual(1, base.c)
        base.validate()
        self.assertEqual({'a': 0, 'b': 0, 'c': 1}, base.serialize())

        other = AnotherChild({'a': 0, 'b': 0, 'c': 1})
        other.validate()

    def test_bad_field_type_typing(self):
        class BadType(Model):
            set: Set[int]

        with self.assertRaises(ConfigurationError) as ctx:
            BadType()
        self.assertEqual("Field set of BadType: Unrecognized field annotation typing.Set[int] "
                         "(may need an explicit Field)", str(ctx.exception))

    def test_bad_field_type_native(self):
        class BadType(Model):
            bad: complex

        with self.assertRaises(ConfigurationError) as ctx:
            BadType()
        self.assertEqual("Field bad of BadType: Unrecognized field annotation complex (may need an explicit Field)",
                         str(ctx.exception))

    def test_multiple_non_abstract_bases(self):
        class Base1(Model):
            a: int

        class Base2(Model):
            b: int

        with self.assertRaises(ConfigurationError) as ctx:
            class Parent(Base1, Base2):
                unused: Parent
        self.assertEqual('Parent: multiple bases have instance lay-out conflict, if inheriting from multiple models, '
                         'only one may have __slots__ (declare abstract models without __slots__ by adding class '
                         'attribute `__abstract__ = True`)', str(ctx.exception))

    def test_none_primitive_name(self):
        class NonePrimitive(Model):
            normal: bool = BoolField(primitive_name='ok', to_primitive_name='ordinary')
            none_both: int = IntField(primitive_name=None)
            none_input: float = FloatField(primitive_name=None, to_primitive_name='no_input')
            none_output: str = StrField(to_primitive_name=None)

        model = NonePrimitive({'ok': True, 'none_both': 1, 'none_input': 4.2, 'no_input': 4.7, 'none_output': 'data'})
        self.assertIs(True, model.normal)
        self.assertIs(Missing, model.none_both)
        self.assertIs(Missing, model.none_input)
        self.assertEqual('data', model.none_output)
        self.assertEqual({'ordinary': True}, model.serialize())

        model.none_both = 5
        model.none_input = 42.47
        model.none_output = 'changed'
        self.assertEqual({'ordinary': True, 'no_input': 42.47}, model.serialize())
        self.assertEqual(5, model.none_both)
        self.assertEqual('changed', model.none_output)

    def test_equality(self):
        model = DriedLeaf({'age': 4.2})
        self.assertEqual(DriedLeaf({'color': 'green', 'age': 4.2}), model)
        self.assertNotEqual(DriedLeaf({'color': 'green', 'age': 4.7}), model)
        self.assertNotEqual(DriedLeaf({'color': None, 'age': 4.2}), model)
        self.assertNotEqual(Leaf({'color': 'green', 'age': 4.2}), model)
        self.assertNotEqual(1, model)
        self.assertNotEqual(None, model)

    def test_override_field_type(self):
        class First(Model):
            plain: int
            custom: int = IntField(min_value=1)

        class Second(First):
            plain: float
            custom: float = FloatField(min_value=2)

        self.assertEqual({'plain': 1.1, 'custom': 2.2}, Second({'plain': '1.1', 'custom': '2.2'}).serialize())

    def test_resolve_extra_types_error(self):
        class Inner(Model):
            pass

        class Outer(Model):
            field: Inner

        with self.assertRaises(ConfigurationError) as e:
            Outer()
        self.assertEqual("Model Outer annotation name 'Inner' is not defined. If not a global symbol or cannot be "
                         "imported globally, use the class method `resolve_extra_types` to provide it.",
                         str(e.exception))

    def test_copy(self):
        class Dummy(Model):
            type = 'dummy'
            field: List[int] = list

        class CopyRight(Model):
            atomic: float
            any: Any
            atomic_list: List[str]
            complex_list: Optional[List[List[bool]]] = None
            atomic_dict: Dict[int, bool] = DictField(hide_none=True)
            complex_dict: Dict[bool, Dummy]
            model: Dummy
            dynamic_model: Optional[Union[Dummy, Leaf]]
            missing: Any = AnyField(deep_copy=True)

            @classmethod
            def resolve_extra_types(cls) -> Set[Type[Model]]:
                return {Dummy}

        model = CopyRight({'any': None, 'atomic_dict': None, 'dynamic_model': None})
        copied = model.copy(deep=True)
        model.atomic = 4.2
        model.any = {1: {True: False}}
        model.atomic_list = ['x']
        model.complex_list = [[]]
        model.atomic_dict = {1: True}
        model.complex_dict = {True: Dummy({'field': [1]})}
        model.model = None
        model.dynamic_model = Dummy()
        self.assertEqual({'any': None, 'complex_list': None, 'dynamic_model': None}, copied.serialize())

        model.model = Dummy({'field': [1, 2]})
        deep_copy = model.copy(deep=True)
        shallow_copy = model.copy(deep=False)
        model.atomic = 4.7
        model.any[1][False] = True
        model.any = Missing
        model.atomic_list.pop(-1)
        model.complex_list[0].append(True)
        model.complex_list.extend([[False], [True, False]])
        model.atomic_dict.pop(1)
        model.complex_dict[True].field.append(2)
        model.model.field.clear()
        model.dynamic_model.field.append(3)
        self.assertEqual({
            'atomic': 4.7,
            'atomic_list': [],
            'complex_list': [[True], [False], [True, False]],
            'atomic_dict': {},
            'complex_dict': {True: {'field': [1, 2]}},
            'model': {'field': []},
            'dynamic_model': {'type': 'dummy', 'field': [3]},
        }, model.to_primitive())
        self.assertEqual({
            'atomic': 4.2,
            'any': {1: {True: False}},
            'atomic_list': ['x'],
            'complex_list': [[]],
            'atomic_dict': {1: True},
            'complex_dict': {True: {'field': [1]}},
            'model': {'field': [1, 2]},
            'dynamic_model': {'type': 'dummy', 'field': []},
        }, deep_copy.serialize())
        self.assertEqual({
            'atomic': 4.2,
            'any': {1: {True: False, False: True}},
            'atomic_list': [],
            'complex_list': [[True], [False], [True, False]],
            'atomic_dict': {},
            'complex_dict': {True: {'field': [1, 2]}},
            'model': {'field': []},
            'dynamic_model': {'type': 'dummy', 'field': [3]},
        }, shallow_copy.serialize())

        self.assertIs(Missing, shallow_copy.missing)
        self.assertIs(Missing, deep_copy.missing)
        self.assertIs(Missing, copy(shallow_copy.missing))

    def test_any_field(self):
        class WithAny(Model):
            normal: Any
            optional: Optional[Any] = None
            custom: Optional[Any] = AnyField(deep_copy=True, default='x', hide_none=True, primitive_name='customized')
            non_model: Optional[NonModel] = AnyField(default=NonModel, hide_none=True)

            def validate_optional(self, value, _):
                if value:
                    raise ValueError('Must be falsy')

        initial = {'normal': {'x': 1}, 'customized': [1, [], {}], 'non_model': NonModel(x=42)}
        model = WithAny(initial)
        self.assertEqual({'x': 1}, model.normal)
        self.assertIsNone(model.optional)
        self.assertEqual([1, [], {}], model.custom)
        self.assertEqual(42, model.non_model.x)
        initial['customized'][1].append(2)
        initial['customized'].pop(-1)
        model.validate()
        self.assertEqual({
            'normal': {'x': 1},
            'optional': None,
            'customized': [1, [], {}],
            'non_model': NonModel(x=42),
        }, model.serialize())
        self.assertEqual("<WithAny {normal={'x': 1}, optional=None, custom=[1, [], {}], non_model=<42>}>", repr(model))

        model.normal['x'] = 'no copy'
        model.non_model = None
        self.assertEqual({'normal': {'x': 'no copy'}, 'optional': None, 'customized': [1, [], {}]}, model.serialize())
        model.serialize()['customized'][1].append(3)
        self.assertEqual([1, [], {}], model.custom)
        self.assertEqual(
            "<WithAny {normal={'x': 'no copy'}, optional=None, custom=[1, [], {}], non_model=None}>",
            repr(model),
        )

        model = WithAny({'optional': 123})
        self.assertEqual({'optional': 123, 'customized': 'x', 'non_model': NonModel(x=1)}, model.serialize())
        self.assertEqual("<WithAny {normal=Missing, optional=123, custom='x', non_model=<1>}>", repr(model))
        with self.assertRaises(ValidationError) as e:
            model.validate()
        self.assertEqual({
            'normal': ['This field is required'],
            'optional': ['Must be falsy'],
        }, e.exception.errors)

    def test_any_field_configuration_error_none_default(self):
        class Bad(Model):
            bad: Any = None

        with self.assertRaises(ConfigurationError) as e:
            Bad()
        self.assertEqual("Field bad of Bad: Cannot use None as default on a non-Optional Field", str(e.exception))

    def test_inheritance_from_non_model(self):
        class NonModel:
            some_attribute: str = "abc"

        class BaseModel(Model):
            x: int

        class MyModel(BaseModel, NonModel):
            some_field: str = "xyz"

        model = MyModel({"some_attribute": "ignore me", "x": 42})
        self.assertEqual("abc", model.some_attribute)
        self.assertEqual(42, model.x)
        self.assertEqual("xyz", model.some_field)
        model.validate()
        self.assertEqual({"x": 42, "some_field": "xyz"}, model.serialize())

    def test_abstract_model_from_concrete_with_slots(self):
        class Concrete(Model):
            x: int

        class Abstract(Concrete):
            __abstract__ = True
            __slots__ = ['a']
            y: float

        class AnotherConcrete(Concrete):
            __slots__ = ['b']
            z: str

        class Merged(Abstract, AnotherConcrete):
            __slots__ = ['c']

        model = Merged({'x': 1.0, 'y': 2, 'z': 3, 'a': 'ignore'})
        self.assertEqual(1, model.x)
        self.assertEqual(2.0, model.y)
        self.assertEqual('3', model.z)
        model.a = model.b = model.c = 'have slots'
        self.assertEqual('have slots', model.a)
        self.assertEqual('have slots', model.b)
        self.assertEqual('have slots', model.c)
        self.assertEqual({'x': 1, 'y': 2.0, 'z': '3'}, model.to_primitive())

    def test_resolve_extra_types_inheritance(self):
        class A(Model):
            a: int = 1

        class B(Model):
            b: float = 2.

        class X(Model):
            a: A = A

            @classmethod
            def resolve_extra_types(cls) -> Set[Type[Model]]:
                return {A}

        class Y(X):
            b: B = B

            @classmethod
            def resolve_extra_types(cls) -> Set[Type[Model]]:
                return {B} | super().resolve_extra_types()

        self.assertEqual({'a': {'a': 1}, 'b': {'b': 2}}, Y().to_primitive())

    def test_missing_singleton_copy(self):
        class ProduceMissing(Model):
            required: int

        model = ProduceMissing()
        self.assertIs(Missing, model.required)
        self.assertIs(Missing, copy(model).required)
        self.assertIs(Missing, deepcopy(model).required)
        self.assertEqual({}, model.serialize())
        self.assertEqual({}, copy(model).serialize())
        self.assertEqual({}, deepcopy(model).serialize())

    def test_explicit_field_no_annotation_error(self):
        with self.assertRaises(ConfigurationError) as ctx:
            class NoAnnotation(Model):
                some_field = StrField(max_length=5)

            _ = NoAnnotation
        self.assertEqual("Field some_field of Model class NoAnnotation defines an explicit Field "
                         "but lacks a type annotation or isn't public", str(ctx.exception))
        with self.assertRaises(ConfigurationError) as ctx:
            class Private(Model):
                _private: str = StrField(max_length=5)

            _ = Private
        self.assertEqual("Field _private of Model class Private defines an explicit Field "
                         "but lacks a type annotation or isn't public", str(ctx.exception))

    def test_get_field(self):
        model = PropertyAccess({'basic_field': 'help'})
        model.extra_slot = 'slot'

        # With value
        self.assertEqual('help', model.get('basic_field'))
        self.assertEqual('help', model.get('basic_serializable'))
        self.assertEqual('help', model.get('basic_property'))
        self.assertEqual('slot', model.get('extra_slot'))

        # With default value
        self.assertEqual('hello', model.get('default_field'))
        self.assertEqual('hello', model.get('default_serializable'))
        self.assertEqual('hello', model.get('default_property'))

        # Missing value
        incomplete_model = PropertyAccess()
        self.assertIsNone(incomplete_model.get('basic_field'))
        self.assertEqual('unknown', incomplete_model.get('basic_field', 'unknown'))
        self.assertIsNone(incomplete_model.get('basic_serializable'))
        self.assertEqual('unknown', incomplete_model.get('basic_serializable', 'unknown'))
        self.assertIsNone(incomplete_model.get('basic_property'))
        self.assertEqual('unknown', incomplete_model.get('basic_property', 'unknown'))

        # Non-existent field, method or unused slot
        incomplete_model = PropertyAccess()
        self.assertIsNone(incomplete_model.get('doesnt_exist'))
        self.assertEqual('unknown', model.get('doesnt_exist', 'unknown'))
        self.assertIsNone(incomplete_model.get('get'))
        self.assertEqual('unknown', model.get('get', 'unknown'))
        self.assertIsNone(incomplete_model.get('extra_slot'))
        self.assertEqual('unknown', incomplete_model.get('extra_slot', 'unknown'))

    def test_getitem(self):
        model = PropertyAccess({'basic_field': 'help'})
        model.extra_slot = 'slot'

        # With value
        self.assertEqual('help', model['basic_field'])
        self.assertEqual('help', model['basic_serializable'])
        self.assertEqual('help', model['basic_property'])
        self.assertEqual('slot', model['extra_slot'])

        # With default value
        self.assertEqual('hello', model['default_field'])
        self.assertEqual('hello', model['default_serializable'])
        self.assertEqual('hello', model['default_property'])

        # Missing value
        incomplete_model = PropertyAccess()
        self.assertIs(Missing, incomplete_model['basic_field'])
        self.assertIs(Missing, incomplete_model['basic_serializable'])
        self.assertIs(Missing, incomplete_model['basic_property'])

        # Non-existent field, method or unused slot
        with self.assertRaisesRegex(KeyError, "'doesnt_exist'"):
            self.fail(f'should raise: {model["doesnt_exist"]}')
        with self.assertRaisesRegex(KeyError, "'get'"):
            self.fail(f'should raise: {model["get"]}')
        with self.assertRaisesRegex(KeyError, "'extra_slot'"):
            self.fail(f'should raise: {incomplete_model["extra_slot"]}')

    def test_ensure_missing_coverage(self):
        # The only purpose of this test is to ensure 100% coverage for *dead* code, where possible
        self.assertEqual(1, IntField().to_primitive(1))

        class Temp(Model):
            field: int

        Temp()

        # noinspection PyAbstractClass
        class FakeField(Field):
            atomic = False
            type = set

        fake_field = FakeField()
        fake_field.name = 'field'
        list(fake_field.validate(42, {}))
        fake_field.copy_value(42)
        Temp.__fields__[0] = fake_field

        with self.assertRaises(AssertionError):
            DataError([])
