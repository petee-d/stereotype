from __future__ import annotations

from typing import Optional, Union, List, Dict, cast, Iterable, Any
from unittest import TestCase

from stereotype import Model, Missing, ValidationError, ConversionError, ModelField, ConfigurationError, ListField, \
    StrField, BoolField, FloatField, DEFAULT_ROLE
from stereotype.fields.compound import DictField
from stereotype.roles import RequestedRoleFields, Role
from stereotype.utils import ToPrimitiveContextType
from tests.common import PrivateStrField


class MyBoolModel(Model):
    type = 'bool'
    field: bool
    bad_field: Optional[bool] = BoolField(default=None, hide_none=True)

    def validate_bad_field(self, value: Optional[bool], _):
        if value is True:
            raise ValueError('Nope')


class MyStrModel(Model):
    type = 'str'
    field: str = StrField(default='', max_length=3)


class SomeLists(Model):
    ints: List[int]
    optionals: List[Optional[str]] = ListField(StrField(min_length=2))
    lists: List[List[float]] = list
    models: Optional[List[MyBoolModel]] = None
    dynamics: List[Union[MyBoolModel, MyStrModel]] = ListField(primitive_name='union')


class SimpleInt(Model):
    int: int


class TestListType(TestCase):
    def test_empty(self):
        model = SomeLists()
        self.assertIs(Missing, model.ints)
        self.assertIs(Missing, model.optionals)
        self.assertEqual([], model.lists)
        self.assertIsNone(model.models)
        self.assertIs(Missing, model.dynamics)
        self.assertEqual('<SomeLists {ints=Missing, optionals=Missing, lists=[], models=None, dynamics=Missing}>',
                         repr(model))
        self.assertEqual({'lists': [], 'models': None}, model.serialize())
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual({
            'ints': ['This field is required'],
            'optionals': ['This field is required'],
            'union': ['This field is required'],
        }, ctx.exception.errors)

        self.assertEqual('<SomeLists {ints=Missing, optionals=Missing, lists=[], models=None, dynamics=Missing}>',
                         repr(model))
        self.assertEqual('<Field ints of type List[int], required>', repr(SomeLists.__fields__[0]))
        self.assertEqual('<Field optionals of type List[str], required>', repr(SomeLists.__fields__[1]))

    def test_basic(self):
        model = SomeLists({
            'ints': [4.0, 5, 6],
            'optionals': ['None', None],
            'lists': [[1], [2, 2.2]],
            'models': [{'field': True}],
            'union': [{'type': 'str'}, {'type': 'bool', 'field': False}],
        })
        self.assertEqual([4, 5, 6], model.ints)
        self.assertIsInstance(model.ints[0], int)
        self.assertEqual(['None', None], model.optionals)
        self.assertEqual([[1], [2, 2.2]], model.lists)
        self.assertIsInstance(model.lists[0][0], float)
        self.assertEqual([MyBoolModel({'field': True})], model.models)
        self.assertEqual([MyStrModel({'field': ''}), MyBoolModel({'field': False})], model.dynamics)
        model.validate()
        self.assertEqual({
            'ints': [4, 5, 6],
            'optionals': ['None', None],
            'lists': [[1.], [2., 2.2]],
            'models': [{'field': True}],
            'union': [{'type': 'str', 'field': ''}, {'type': 'bool', 'field': False}],
        }, model.serialize())
        self.assertEqual('<SomeLists {ints=[(3 items)], optionals=[(2 items)], lists=[(2 items)], models=[(1 items)], '
                         'dynamics=[(2 items)]}>', repr(model))

    def test_inner_validation(self):
        data = {
            'ints': [None, 5],
            'optionals': ['xyz', 'a', None, 'b'],
            'lists': [[1], [None, 2.2]],
            'models': [None, {'bad_field': True}],
            'union': [{'type': 'bool', 'field': False}, {'type': 'str', 'field': '01234'}],
        }
        model = SomeLists(data)
        self.assertEqual([None, 5], model.ints)
        self.assertEqual(['xyz', 'a', None, 'b'], model.optionals)
        self.assertEqual([[1], [None, 2.2]], model.lists)
        self.assertEqual([None, MyBoolModel({'bad_field': True})], model.models)
        self.assertEqual([MyBoolModel({'field': False}), MyStrModel({'field': '01234'})], model.dynamics)
        self.assertEqual(data, model.serialize())
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual({
            'ints': {'0': ['This field is required']},
            'optionals': {'1': ['Must be at least 2 characters long'], '3': ['Must be at least 2 characters long']},
            'lists': {'1': {'0': ['This field is required']}},
            'models': {'0': ['This field is required'],
                       '1': {'bad_field': ['Nope'], 'field': ['This field is required']}},
            'union': {'1': {'field': ['Must be at most 3 characters long']}},
        }, ctx.exception.errors)

    def test_size_validation(self):
        class Sizes(Model):
            min: List[int] = ListField(default=[], min_length=1)
            max: Optional[List[float]] = ListField(default=None, max_length=3)
            exact: List[str] = ListField(min_length=3, max_length=3)
            min_max: List[MyStrModel] = ListField(min_length=1, max_length=3)

        model = Sizes({'max': [1, 2.0, 3.3, 4.4], 'exact': ['a', 'b'], 'min_max': []})
        self.assertEqual({'min': [], 'max': [1, 2.0, 3.3, 4.4], 'exact': ['a', 'b'], 'min_max': []}, model.serialize())
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual({
            'min': ['Provide at least 1 item'],
            'max': ['Provide at most 3 items'],
            'exact': ['Provide exactly 3 items'],
            'min_max': ['Provide 1 to 3 items'],
        }, ctx.exception.errors)
        Sizes({'min': ['4'], 'max': None, 'exact': ['a', 'b', 'c'], 'min_max': [{}, {}]}).validate()
        Sizes({'min': ['4', 2], 'max': {'4.2', 0}, 'exact': ['a', 'a', 'a'], 'min_max': [{}, {}, {}]}).validate()
        self.assertIsNot(Sizes().min, Sizes().min)

    def test_field_options(self):
        my_role = Role('my-role')

        class Stuff(Model):
            hide_none: Optional[List[str]] = ListField(hide_none=True)
            hide_empty: Optional[List[str]] = ListField(hide_empty=True, default=None)
            custom_output: List[MyStrModel] = ListField(to_primitive_name='custom')
            no_output: List[int] = ListField(primitive_name='input', to_primitive_name=None)

            @classmethod
            def declare_roles(cls) -> Iterable[RequestedRoleFields]:
                yield my_role.blacklist(cls.custom_output)

        model = Stuff({'hide_none': ['ok'], 'custom': ['nope'], 'custom_output': [{}], 'input': [1, 2]})
        self.assertEqual({'hide_none': ['ok'], 'hide_empty': None, 'custom': [{'field': ''}]}, model.to_primitive())

        model = Stuff({'hide_none': None, 'hide_empty': [], 'custom_output': [{'field': 'abc'}]})
        self.assertEqual({}, model.to_primitive(my_role))
        self.assertEqual({'custom': [{'field': 'abc'}]}, model.to_primitive())

    def test_nested_conversion_errors(self):
        class Collections(Model):
            models: List[SimpleInt]
            ints: List[int]

        with self.assertRaises(ConversionError) as ctx:
            Collections({'models': [{'int': 1}, {'int': 'nan'}, {'int': 'bad'}]})
        self.assertEqual({'models': {'1': {'int': ["Value 'nan' is not an integer number"]}}}, ctx.exception.errors)

        with self.assertRaises(ConversionError) as ctx:
            Collections({'ints': ['bad', 'worse']})
        self.assertEqual({'ints': {'0': ["Value 'bad' is not an integer number"]}}, ctx.exception.errors)

    def test_configuration_error_not_list(self):
        class Bad(Model):
            mismatch: Dict[str, MyStrModel] = ListField(item_field=ModelField())

        with self.assertRaises(ConfigurationError) as ctx:
            Bad()
        self.assertEqual('Field mismatch: ListField cannot be used for annotation typing.Dict[str, '
                         'tests.test_compound_fields.MyStrModel], should use DictField', str(ctx.exception))

    def test_configuration_error_list_item_mismatch(self):
        class Bad(Model):
            worse: List[Optional[bool]] = ListField(item_field=StrField(hide_none=True))

        with self.assertRaises(ConfigurationError) as ctx:
            Bad()
        self.assertEqual('Field worse: StrField cannot be used for annotation bool, should use BoolField',
                         str(ctx.exception))

    def test_to_primitive_context(self):
        class Stuff(Model):
            lst: List[str] = ListField(PrivateStrField())
        model = Stuff({'lst': ['one', 'two']})
        serialized = model.to_primitive(context={'private': True})
        self.assertEqual(serialized['lst'], ['<hidden>', '<hidden>'])


class MyDicts(Model):
    int_to_int: Dict[int, int]
    str_to_floats: Dict[str, List[float]] = DictField(StrField(min_length=2), default=lambda: {'xy': []})
    bool_to_model: Optional[Dict[bool, MyBoolModel]] = None
    str_to_opt_dict: Dict[str, Optional[Dict[int, int]]] = DictField(value_field=DictField(min_length=1),
                                                                     hide_empty=True)


class TestDictType(TestCase):
    def test_empty(self):
        model = MyDicts()
        self.assertIs(Missing, model.int_to_int)
        self.assertEqual({'xy': []}, model.str_to_floats)
        self.assertIsNone(model.bool_to_model)
        self.assertIs(Missing, model.str_to_opt_dict)
        self.assertEqual({'str_to_floats': {'xy': []}, 'bool_to_model': None}, model.serialize())
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual({
            'int_to_int': ['This field is required'],
            'str_to_opt_dict': ['This field is required'],
        }, ctx.exception.errors)

        self.assertEqual('<MyDicts {int_to_int=Missing, str_to_floats={(1 items)}, bool_to_model=None, '
                         'str_to_opt_dict=Missing}>', repr(model))
        self.assertEqual('<Field int_to_int of type Dict[int, int], required>', repr(MyDicts.__fields__[0]))

        model.str_to_floats = {}
        model.str_to_opt_dict = {}
        self.assertEqual({'bool_to_model': None, 'str_to_floats': {}}, model.serialize())
        self.assertEqual('<MyDicts {int_to_int=Missing, str_to_floats={}, bool_to_model=None, '
                         'str_to_opt_dict={}}>', repr(model))

    def test_empty_default(self):
        class EmptyDicts(Model):
            callable: Dict[str, str] = dict
            kwarg: Dict[int, int] = DictField(default={}, hide_empty=True)
            direct: Dict[float, float] = {}

        empty = EmptyDicts()
        self.assertEqual({}, empty.kwarg)
        self.assertEqual({'callable': {}, 'direct': {}}, empty.serialize())
        self.assertIsNot(empty.callable, EmptyDicts().callable)
        self.assertIsNot(empty.kwarg, EmptyDicts().kwarg)
        self.assertIsNot(empty.direct, EmptyDicts().direct)

    def test_field_validators(self):
        def keys_different_from_values(value, _):
            if any(key == value for key, value in value.items()):
                raise ValueError("Keys must be different from their values")

        def keys_same_as_values(value, _):
            if any(key != value for key, value in value.items()):
                raise ValueError("Keys must be same as their values")

        class Impossible(Model):
            futile: Dict[str, str] = DictField(validators=[keys_different_from_values, keys_same_as_values])

        with self.assertRaises(ValidationError) as ctx:
            Impossible({'futile': {'same': 'same', 'what': 'ever'}}).validate()
        self.assertEqual({
            'futile': ['Keys must be different from their values', 'Keys must be same as their values'],
        }, ctx.exception.errors)

        with self.assertRaises(ValidationError) as ctx:
            Impossible({'futile': {'different': 'value', 'one': 'another'}}).validate()
        self.assertEqual({'futile': ['Keys must be same as their values']}, ctx.exception.errors)

    def test_basic(self):
        model = MyDicts({
            'int_to_int': {1: 2, 3.0: 4.0},
            'str_to_floats': {},
            'bool_to_model': {True: {'field': False}},
            'str_to_opt_dict': {'x': {'1': 2.0}, 'y': {3.0: '4'}},
        })
        self.assertEqual({1: 2, 3.0: 4.0}, model.int_to_int)
        self.assertEqual({}, model.str_to_floats)
        self.assertEqual({True: MyBoolModel({'field': False})}, model.bool_to_model)
        self.assertEqual({'x': {1: 2}, 'y': {3: 4}}, model.str_to_opt_dict)
        model.validate()
        self.assertEqual({
            'int_to_int': {1: 2, 3.0: 4.0},
            'str_to_floats': {},
            'bool_to_model': {True: {'field': False}},
            'str_to_opt_dict': {'x': {1: 2}, 'y': {3: 4}},
        }, model.serialize())
        self.assertEqual('<MyDicts {int_to_int={(2 items)}, str_to_floats={}, bool_to_model={(1 items)}, '
                         'str_to_opt_dict={(2 items)}}>', repr(model))

    def test_conversion_errors(self):
        data = cast(dict, {
            'int_to_int': {1: 2, 4.2: 4.7},
            'str_to_floats': ['xyz'],
            'bool_to_model': {1: None},
            'str_to_opt_dict': {4: 2},
        })
        with self.assertRaises(ConversionError) as ctx:
            MyDicts(data)
        self.assertEqual({
            'int_to_int': {'4.2': ['Numeric value 4.2 is not an integer']},
        }, ctx.exception.errors)

        data['int_to_int'] = {1: 2, 4: 4.7}
        with self.assertRaises(ConversionError) as ctx:
            MyDicts(data)
        self.assertEqual({
            'int_to_int': {'4': ['Numeric value 4.7 is not an integer']},
        }, ctx.exception.errors)

        data['int_to_int'][4] = 7
        with self.assertRaises(ConversionError) as ctx:
            MyDicts(data)
        self.assertEqual({
            'str_to_floats': ['Expected a dict, got a list'],
        }, ctx.exception.errors)

        data['str_to_floats'] = {'xyz': ['4.2']}
        with self.assertRaises(ConversionError) as ctx:
            MyDicts(data)
        self.assertEqual({
            'bool_to_model': {'1': ['Value must be a boolean or a true/false/yes/no string value']},
        }, ctx.exception.errors)

        data['bool_to_model'] = {True: None}
        with self.assertRaises(ConversionError) as ctx:
            MyDicts(data)
        self.assertEqual({
            'str_to_opt_dict': {'4': ['Expected a dict, got a int']},
        }, ctx.exception.errors)

        data['str_to_opt_dict'][4] = None
        MyDicts(data)

    def test_nested_conversion_errors(self):
        class Collections(Model):
            models: Dict[str, SimpleInt]
            ints: Dict[str, int]

        with self.assertRaises(ConversionError) as ctx:
            Collections({'models': {'x': {'int': 'bad'}, 'y': {'int': 2}, '3': {'int': 'y'}}})
        self.assertEqual({'models': {'x': {'int': ["Value 'bad' is not an integer number"]}}}, ctx.exception.errors)

        with self.assertRaises(ConversionError) as ctx:
            Collections({'ints': {'x': 1, 'y': '2+3', 'z': 'y'}})
        self.assertEqual({'ints': {'y': ["Value '2+3' is not an integer number"]}}, ctx.exception.errors)

    def test_inner_validation(self):
        data = {
            'int_to_int': None,
            'str_to_floats': {'a': [4.7, None, 42]},
            'bool_to_model': {None: {'field': False}, True: {'field': True, 'bad_field': True}, False: None},
            'str_to_opt_dict': {'x': {1: 2}, 'y': {}},
        }
        model = MyDicts(data)
        self.assertIs(None, model.int_to_int)
        self.assertEqual({'a': [4.7, None, 42]}, model.str_to_floats)
        self.assertEqual({
            None: MyBoolModel({'field': False}),
            True: MyBoolModel({'field': True, 'bad_field': True}),
            False: None,
        }, model.bool_to_model)
        self.assertEqual({'x': {1: 2}, 'y': {}}, model.str_to_opt_dict)
        self.assertEqual(data, model.serialize())
        self.assertIsInstance(model.serialize()['str_to_floats']['a'][2], float)
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual({
            'int_to_int': ['This field is required'],
            'str_to_floats': {'a': {'1': ['This field is required'],
                                    '_global': ['Must be at least 2 characters long']}},
            'bool_to_model': {'None': ['This field is required'],
                              'True': {'bad_field': ['Nope']},
                              'False': ['This field is required']},
            'str_to_opt_dict': {'y': ['Provide at least 1 item']},
        }, ctx.exception.errors)

    def test_double_required_error(self):
        class RequiredDict(Model):
            dict: Dict[int, int]

        model = RequiredDict({'dict': {4: 2}})
        model.validate()
        self.assertEqual(2, model.dict[4])
        with self.assertRaises(ValidationError) as ctx:
            RequiredDict({'dict': {None: None}}).validate()
        self.assertEqual('dict: None: This field is required', str(ctx.exception))

    def test_configuration_error_not_dict(self):
        class Bad(Model):
            mismatch: List[MyStrModel] = DictField(key_field=BoolField(), value_field=ModelField())

        with self.assertRaises(ConfigurationError) as ctx:
            Bad()
        self.assertEqual('Field mismatch: DictField cannot be used for annotation '
                         'typing.List[tests.test_compound_fields.MyStrModel], should use ListField', str(ctx.exception))

    def test_configuration_error_invalid_key(self):
        class InvalidKey(Model):
            bad: Dict[MyStrModel, bool]

        with self.assertRaises(ConfigurationError) as ctx:
            InvalidKey()
        self.assertEqual('Field bad: DictField keys may only be booleans, numbers or strings: '
                         'typing.Dict[tests.test_compound_fields.MyStrModel, bool]', str(ctx.exception))

    def test_configuration_error_dict_key_mismatch(self):
        class Bad(Model):
            bad: Dict[int, bool] = DictField(key_field=FloatField())

        with self.assertRaises(ConfigurationError) as ctx:
            Bad()
        self.assertEqual('Field bad: FloatField cannot be used for annotation int, should use IntField',
                         str(ctx.exception))

    def test_configuration_error_dict_value_mismatch(self):
        class Bad(Model):
            worse: Dict[int, bool] = DictField(value_field=ModelField())

        with self.assertRaises(ConfigurationError) as ctx:
            Bad()
        self.assertEqual('Field worse: ModelField cannot be used for annotation bool, should use BoolField',
                         str(ctx.exception))

    def test_to_primitive_context(self):
        class Stuff(Model):
            dct: Dict[str, str] = DictField(value_field=PrivateStrField())

        model = Stuff({'dct': {
            'one': 'foo',
            'two': 'bar',
        }})
        serialized = model.to_primitive(context={'private': True})
        self.assertEqual(serialized['dct'], {
            'one': '<hidden>',
            'two': '<hidden>',
        })
