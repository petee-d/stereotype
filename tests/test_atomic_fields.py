from __future__ import annotations

import re
from typing import Optional
from unittest import TestCase

from stereotype import Model, Missing, ValidationError, ConversionError, BoolField, IntField, ConfigurationError, \
    FloatField, StrField, DEFAULT_ROLE
from tests.common import PrivateStrField


class BoolModel(Model):
    req: bool
    opt: Optional[bool]
    req_def: bool = True
    opt_def: Optional[bool] = None


class TestBooleanField(TestCase):
    def test_empty(self):
        model = BoolModel()
        self.assertIs(Missing, model.req)
        self.assertIs(Missing, model.opt)
        self.assertIs(True, model.req_def)
        self.assertIs(None, model.opt_def)
        self.assertFalse(model.req)
        self.assertEqual('<BoolModel {req=Missing, opt=Missing, req_def=True, opt_def=None}>', str(model))
        self.assertEqual('<BoolModel {req=Missing, opt=Missing, req_def=True, opt_def=None}>', repr(model))
        self.assertEqual({'req_def': True, 'opt_def': None}, model.serialize())
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual('req: This field is required', str(ctx.exception))
        self.assertEqual({'req': ['This field is required'], 'opt': ['This field is required']}, ctx.exception.errors)

        self.assertEqual('<Field req of type bool, required>', repr(BoolModel.__fields__[0]))

    def test_special(self):
        class BoolSpecialModel(Model):
            plain: bool = False
            hidden: Optional[bool] = BoolField(hide_none=True)
            changed: bool = BoolField(primitive_name='other', hide_false=True)
            weird: Optional[bool] = BoolField(primitive_name='input', to_primitive_name='output', default=True)

        model = BoolSpecialModel({'hidden': None, 'changed': 'ignore', 'other': True, 'output': False, 'weird': False})
        self.assertIs(False, model.plain)
        self.assertIs(None, model.hidden)
        self.assertIs(True, model.changed)
        self.assertIs(True, model.weird)
        self.assertEqual({'plain': False, 'other': True, 'output': True}, model.serialize())
        model.validate()

        model.hidden = True
        model.changed = False
        model.weird = False
        self.assertEqual({'plain': False, 'hidden': True, 'output': False}, model.serialize())
        model.validate()

        model.changed = None
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual({'other': ['This field is required']}, ctx.exception.errors)

        self.assertEqual('<Field plain of type bool, default=<False>>', repr(BoolSpecialModel.__fields__[0]))

    def test_bad_values(self):
        model = BoolModel({'req': None, 'opt': 'No', 'opt_def': 'true'})
        self.assertIs(None, model.req)
        self.assertIs(False, model.opt)
        self.assertIs(True, model.req_def)
        self.assertIs(True, model.opt_def)
        self.assertEqual('<BoolModel {req=None, opt=False, req_def=True, opt_def=True}>', repr(model))
        self.assertEqual({'req': None, 'opt': False, 'req_def': True, 'opt_def': True}, model.to_primitive())
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual('req: This field is required', str(ctx.exception))
        self.assertEqual({'req': ['This field is required']}, ctx.exception.errors)

    def test_bad_types(self):
        with self.assertRaises(ConversionError) as ctx:
            BoolModel({'req': 'bad', 'opt': 4, 'opt_def': 'true'})
        self.assertEqual('req: Value must be a boolean or a true/false/yes/no string value', str(ctx.exception))
        with self.assertRaises(ConversionError) as ctx:
            BoolModel({'opt': 4, 'opt_def': 'false'})
        self.assertEqual({'opt': ['Value must be a boolean or a true/false/yes/no string value']}, ctx.exception.errors)

    def test_bad_default(self):
        class NotBool(Model):
            value: bool = 42

        with self.assertRaises(ConfigurationError) as ctx:
            NotBool()
        self.assertEqual('Value `42` used as field default must be of type bool', str(ctx.exception))


def is_even(value, context):
    if value % 2 == 1:
        raise ValueError(f"Must be an even {context or 'number'}")


class IntModel(Model):
    normal: int = IntField(default=42, primitive_name='norm')
    min: int = IntField(min_value=3)
    max: Optional[int] = IntField(max_value=int(2e10))
    min_max: int = IntField(min_value=5, max_value=10, default=lambda: 8)
    even: int = IntField(default=0, hide_zero=True, validators=[is_even])

    def validate_even(self, value, context):
        if self.max is not None and value > self.max:
            raise ValueError(f"Even an even {context or 'number'} cannot be above max")


class TestIntField(TestCase):
    def test_min_max_validation(self):
        model = IntModel({'norm': -5, 'min': 2, 'max': int(3e10), 'min_max': '17'})
        self.assertEqual(-5, model.normal)
        self.assertEqual(2, model.min)
        self.assertEqual(int(3e10), model.max)
        self.assertEqual(17, model.min_max)
        self.assertEqual(17, model['min_max'])
        self.assertEqual(0, model['even'])
        with self.assertRaises(KeyError) as ctx:
            self.failIf(model['serialize'])
        self.assertEqual("'serialize'", str(ctx.exception))
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual({
            'min': ['Must be at least 3'],
            'max': ['Must be at most 20000000000'],
            'min_max': ['Must be between 5 and 10'],
        }, ctx.exception.errors)
        self.assertEqual({'norm': -5, 'min': 2, 'max': 30000000000, 'min_max': 17}, model.serialize())

        self.assertEqual('<Field normal of type int, default=<42>, primitive name norm>', repr(IntModel.__fields__[0]))

    def test_custom_validators(self):
        model = IntModel({'min': 5, 'max': 5})
        model.validate()
        model.even = 7
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual({
            'even': ['Even an even number cannot be above max', 'Must be an even number'],
        }, ctx.exception.errors)
        with self.assertRaises(ValidationError) as ctx:
            model.validate("integer")
        self.assertEqual({
            'even': ['Even an even integer cannot be above max', 'Must be an even integer'],
        }, ctx.exception.errors)

    def test_conversion_errors(self):
        with self.assertRaises(ConversionError) as ctx:
            IntModel({'min': 2.5, 'max': 100, 'min_max': 'abc'})
        self.assertEqual({'min': ['Numeric value 2.5 is not an integer']}, ctx.exception.errors)
        with self.assertRaises(ConversionError) as ctx:
            IntModel({'max': 100, 'min_max': 'abc'})
        self.assertEqual({'min_max': ["Value 'abc' is not an integer number"]}, ctx.exception.errors)
        with self.assertRaises(ConversionError) as ctx:
            IntModel({'max': '1.5'})
        self.assertEqual({'max': ["Value '1.5' is not an integer number"]}, ctx.exception.errors)

    def test_none_and_defaults(self):
        model = IntModel({'min': 4, 'max': None})
        self.assertEqual(42, model.normal)
        self.assertEqual(4, model.min)
        self.assertIsNone(model.max)
        self.assertEqual(8, model.min_max)
        model.validate()
        self.assertEqual({'norm': 42, 'min': 4, 'max': None, 'min_max': 8}, model.serialize())

    def test_bad_default(self):
        class NotInt(Model):
            field: int = 4.2

        with self.assertRaises(ConfigurationError) as ctx:
            NotInt()
        self.assertEqual('Value `4.2` used as field default must be of type int', str(ctx.exception))

        class NotOptional(Model):
            field: int = None

        with self.assertRaises(ConfigurationError) as ctx:
            NotOptional()
        self.assertEqual('Field `field` is not Optional and cannot use None as default', str(ctx.exception))

    def test_hidden_figures(self):
        class Hidden(Model):
            none: Optional[int] = IntField(hide_none=True)
            zero: Optional[int] = IntField(hide_zero=True)

        self.assertEqual({'none': 0}, Hidden({'none': 0, 'zero': 0}).serialize())
        self.assertEqual({'zero': None}, Hidden({'none': None, 'zero': None}).serialize())


class FloatModel(Model):
    normal: Optional[float] = None
    min: float = FloatField(min_value=4, to_primitive_name='bottom')
    max: Optional[float] = FloatField(max_value=47.42, default=42., primitive_name='top', to_primitive_name='max')
    min_max: float = FloatField(min_value=1.5, max_value=4, default=lambda: 3.5, hide_none=True)

    # noinspection PyMethodMayBeStatic
    def validate_min(self, value: int, _):
        # Would fail if executed with None
        if value % 2 == 0:
            raise ValueError('Must be an odd number')

    def validate_max(self, value: int, _):
        # Executed even with None because max is optional
        if value is None and self.normal is None:
            raise ValueError('Must be set if normal is omitted')


class TestFloatField(TestCase):
    def test_min_max_validation(self):
        FloatModel({'normal': 1, 'min': 47, 'min_max': 1.5}).validate()
        model = FloatModel({'normal': -5.6, 'min': 2, 'top': '50.42', 'min_max': '8', 'max': 'ignore me'})
        self.assertEqual(-5.6, model.normal)
        self.assertEqual(2, model.min)
        self.assertEqual(50.42, model.max)
        self.assertEqual(8, model.min_max)
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual({
            'min': ['Must be at least 4', 'Must be an odd number'],
            'top': ['Must be at most 47.42'],
            'min_max': ['Must be between 1.5 and 4'],
        }, ctx.exception.errors)
        self.assertEqual({'normal': -5.6, 'bottom': 2., 'max': 50.42, 'min_max': 8.}, model.serialize())

        self.assertEqual('<Field normal of type Optional[float], default=<None>>', repr(FloatModel.__fields__[0]))

    def test_custom_validation(self):
        model = FloatModel({'min': 4, 'top': None})
        self.assertEqual(None, model.normal)
        self.assertEqual(4., model.min)
        self.assertEqual(None, model.max)
        self.assertEqual(3.5, model.min_max)
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual({
            'min': ['Must be an odd number'],
            'top': ['Must be set if normal is omitted'],
        }, ctx.exception.errors)
        self.assertEqual({'normal': None, 'bottom': 4., 'max': None, 'min_max': 3.5}, model.serialize())
        model.normal = model.min = 5.
        model.validate()

    def test_none_and_defaults(self):
        model = FloatModel({'min': 5})
        self.assertIsNone(None, model.normal)
        self.assertEqual(5., model.min)
        self.assertEqual(42., model.max)
        self.assertEqual(3.5, model.min_max)
        self.assertTrue(isinstance(model.min, float))
        model.validate()
        self.assertEqual({'normal': None, 'bottom': 5., 'max': 42., 'min_max': 3.5}, model.serialize())

        model.normal = 4.5
        model.min = model.max = model.min_max = None
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual({'min': ['This field is required'], 'min_max': ['This field is required']},
                         ctx.exception.errors)

    def test_mismatched_field(self):
        class Mismatch(Model):
            my_name: int = FloatField(min_value=1)

        with self.assertRaises(ConfigurationError) as ctx:
            Mismatch({'my_name': 5})
        self.assertEqual("Field my_name: FloatField cannot be used for annotation int, should use IntField",
                         str(ctx.exception))

    def test_hidden_figures(self):
        class Hidden(Model):
            none: Optional[float] = FloatField(hide_none=True, default=None)
            zero: Optional[float] = FloatField(hide_zero=True, default=0.0)

        self.assertEqual({}, Hidden({}).serialize())
        self.assertEqual({}, Hidden({'none': None, 'zero': 0}).serialize())
        self.assertEqual({'none': 0, 'zero': None}, Hidden({'none': 0, 'zero': None}).serialize())


class TestStrField(TestCase):
    def test_validation(self):
        class StrModel(Model):
            normal: str
            non_empty: Optional[str] = StrField(min_length=1)
            min: str = StrField(min_length=3)
            max: str = StrField(max_length=1)
            min_max: Optional[str] = StrField(min_length=1, max_length=6)
            exact: str = StrField(min_length=3, max_length=3)
            choices: Optional[str] = StrField(choices=('a', 'bb', 'ccc'))
            reg_str: str = StrField(regex='[a-z]{3,5}', default='abc')
            reg_pattern: Optional[str] = StrField(default=None, regex=re.compile('hello', re.IGNORECASE))

        valid = StrModel({
            'normal': 'a',
            'non_empty': 'abc',
            'min': 'abc',
            'max': '',
            'min_max': 'a',
            'exact': 'abc',
            'choices': 'bb',
        })
        valid.validate()

        model = StrModel({
            'normal': 4,
            'non_empty': '',
            'min': 'x',
            'max': '123',
            'min_max': '',
            'exact': True,
            'choices': 'c',
            'reg_str': 'a/b',
            'reg_pattern': 'HELLo',
        })
        self.assertEqual('4', model.normal)
        self.assertEqual('', model.non_empty)
        self.assertEqual('x', model.min)
        self.assertEqual('123', model.max)
        self.assertEqual('', model.min_max)
        self.assertEqual('True', model.exact)
        self.assertEqual('c', model.choices)
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual({
            'non_empty': ['This value cannot be empty'],
            'min': ['Must be at least 3 characters long'],
            'max': ['Must be at most 1 character long'],
            'min_max': ['Must be 1 to 6 characters long'],
            'exact': ['Must be exactly 3 characters long'],
            'choices': ['Must be one of: a, bb, ccc'],
            'reg_str': ['Must match regex `[a-z]{3,5}`'],
        }, ctx.exception.errors)

        valid.reg_pattern = 'hi'
        with self.assertRaises(ValidationError) as ctx:
            valid.validate()
        self.assertEqual({'reg_pattern': ['Must match regex `hello` (case insensitive)']}, ctx.exception.errors)

        self.assertEqual('<Field non_empty of type Optional[str], required>', repr(StrModel.__fields__[1]))

    def test_bad_validation_combo(self):
        with self.assertRaises(ConfigurationError) as ctx:
            class LengthChoices(Model):
                unused: LengthChoices
                bad: str = StrField(min_length=1, choices=('x', 'y', 'zz'))
        self.assertEqual('Can only validate length, choices or regex; not combinations of these', str(ctx.exception))

        with self.assertRaises(ConfigurationError) as ctx:
            StrField(choices=('x', 'y', 'zz'), regex='x|y|zz')
        self.assertEqual('Can only validate length, choices or regex; not combinations of these', str(ctx.exception))

    def test_hide_empty(self):
        class Hidden(Model):
            none: Optional[str] = StrField(hide_none=True)
            empty: Optional[str] = StrField(hide_empty=True)

        self.assertEqual({'empty': None}, Hidden({'none': None, 'empty': None}).serialize())
        self.assertEqual({'none': ''}, Hidden({'none': '', 'empty': ''}).serialize())


class TestFieldCommon(TestCase):
    def test_validators(self):
        def not_1(value, _):
            if value == 1:
                raise ValueError('Not that one')

        class Validators(Model):
            default: Optional[int] = IntField(default=None, validators=[not_1])
            optional: Optional[float] = FloatField(validators=[is_even, not_1])
            required: float = FloatField(validators=[not_1, is_even])

        with self.assertRaises(ValidationError) as ctx:
            Validators({'required': None}).validate()
        self.assertEqual({
            'optional': ['This field is required'],  # Validators don't trigger for missing required fields
            'required': ['This field is required'],  # Validators don't trigger for None non-optional fields
        }, ctx.exception.errors)

        with self.assertRaises(ValidationError) as ctx:
            Validators({'default': 1, 'optional': 1, 'required': 1}).validate(context='amount')
        self.assertEqual({
            'default': ['Not that one'],  # Tests validators force inclusion in __validated_fields__
            'optional': ['Must be an even amount', 'Not that one'],  # Order same as the order of validators
            'required': ['Not that one', 'Must be an even amount'],
        }, ctx.exception.errors)


class TestCustomStrField(TestCase):
    def test_to_primitive_context(self):
        class SensitiveModel(Model):
            sensitive: str = PrivateStrField(min_length=1)

        model = SensitiveModel({'sensitive': 'private stuff'})
        self.assertEqual(model.to_primitive(), {'sensitive': 'private stuff'})
        self.assertEqual(model.to_primitive(context={'private': True}), {'sensitive': '<hidden>'})
