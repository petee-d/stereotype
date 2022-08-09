from __future__ import annotations

from typing import Optional, Union, Type, Set
from unittest import TestCase

from stereotype import Model, Missing, ValidationError, ConversionError, ModelField, DynamicModelField, \
    ConfigurationError, IntField, DEFAULT_ROLE
from tests.common import Leaf


class Fake(object):
    type = 'fake'


class Branch(Model):
    type = 'branch'

    leaf: Leaf
    branch: Optional[Branch] = ModelField(default=None, hide_none=True, primitive_name='sub-branch')


class Trunk(Model):
    left: Optional[Union[Branch, Leaf]] = None
    right: Union[Leaf, None, Branch] = DynamicModelField(default=lambda: None, primitive_name='right')

    def validate_right(self, value: Optional[Union[Branch, Leaf]], _):
        if isinstance(value, Branch) and value.leaf.color == 'green':
            raise ValueError('Trees cannot have green leaves on the right side')

    def to_primitive(self, role=DEFAULT_ROLE, context=None):
        serialized = super().to_primitive(role, context)
        if context is not None and context.get('private', False):
            serialized['left'] = serialized['right'] = '<hidden>'
        return serialized


class Root(Model):
    depth: int
    trunk: Optional[Trunk] = Trunk


class TestModelType(TestCase):
    def test_empty(self):
        model = Branch()
        self.assertIs(Missing, model.leaf)
        self.assertIs(None, model.branch)
        self.assertEqual('<Branch {leaf=Missing, branch=None}>', repr(model))
        self.assertEqual({}, model.serialize())
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual('leaf: This field is required', str(ctx.exception))
        self.assertEqual({'leaf': ['This field is required']}, ctx.exception.errors)

        self.assertEqual('<Field leaf of type Leaf, required>', repr(Branch.__fields__[0]))

    def test_simple(self):
        model = Branch({'leaf': {'color': 'red'}})
        self.assertEqual(Leaf({'color': 'red'}), model.leaf)
        self.assertIs(None, model.branch)
        self.assertEqual('<Branch {leaf=Leaf, branch=None}>', repr(model))
        self.assertEqual({'leaf': {'color': 'red'}}, model.serialize())
        model.validate()

    def test_recursive(self):
        model = Branch({'leaf': Leaf({'color': 'yellow'}), 'sub-branch': {'leaf': {}}})
        self.assertEqual(Leaf({'color': 'yellow'}), model.leaf)
        self.assertEqual(Branch({'leaf': {'color': 'green'}}), model.branch)
        self.assertEqual('green', model.branch.leaf.color)
        self.assertEqual('<Branch {leaf=Leaf, branch=Branch}>', repr(model))
        self.assertEqual({'leaf': {'color': 'yellow'}, 'sub-branch': {'leaf': {'color': 'green'}}}, model.serialize())
        model.validate()

    def test_hide_empty(self):
        class MayBeEmpty(Model):
            no_zero: int = IntField(hide_zero=True, default=0)

        class Container(Model):
            maybe: MayBeEmpty = ModelField(hide_empty=True, default=MayBeEmpty)

            @classmethod
            def resolve_extra_types(cls) -> Set[Type[Model]]:
                return {MayBeEmpty}

        self.assertEqual({'maybe': {'no_zero': 1}}, Container({'maybe': {'no_zero': 1}}).serialize())
        self.assertEqual({}, Container({'maybe': {'no_zero': 0}}).serialize())
        self.assertEqual({}, Container().serialize())

    def test_bad_type(self):
        with self.assertRaises(ConversionError) as ctx:
            Branch({'leaf': 'yellow'})
        self.assertEqual({'leaf': ['Supplied type str, needs a mapping or Leaf']}, ctx.exception.errors)
        with self.assertRaises(ConversionError) as ctx:
            Branch({'leaf': Branch()})
        self.assertEqual({'leaf': ['Supplied type Branch, needs a mapping or Leaf']}, ctx.exception.errors)
        with self.assertRaises(ValidationError) as ctx:
            Branch({'leaf': None}).validate()
        self.assertEqual({'leaf': ['This field is required']}, ctx.exception.errors)

    def test_default_model(self):
        model = Root()
        self.assertIs(Missing, model.depth)
        self.assertEqual(Trunk(), model.trunk)
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual('depth: This field is required', str(ctx.exception))
        model.depth = 2
        model.validate()
        self.assertIsNone(model.trunk.left)
        model.trunk = None
        self.assertEqual({'depth': 2, 'trunk': None}, model.serialize())

    def test_to_primitive_context(self):
        model = Root({'depth': 2})
        self.assertEqual(
            model.to_primitive(context={'private': True}),
            {'depth': 2, 'trunk': {'left': '<hidden>', 'right': '<hidden>'}}
        )


class TestDynamicModelField(TestCase):
    def test_empty(self):
        model = Trunk()
        self.assertIsNone(model.left)
        self.assertIsNone(model.right)
        model.validate()
        self.assertEqual({'left': None, 'right': None}, model.to_primitive())
        self.assertEqual('<Field left of type Optional[Union[Branch, Leaf]], default=<None>>',
                         repr(Trunk.__fields__[0]))

    def test_mixed(self):
        model = Trunk({'left': {'type': 'branch', 'leaf': {'color': 'yellow'}}, 'right': Leaf({'color': 'red'})})
        self.assertEqual(Branch({'leaf': {'color': 'yellow'}}), model.left)
        self.assertEqual(Leaf({'color': 'red'}), model.right)
        model.validate()
        self.assertEqual({'left': {'type': 'branch', 'leaf': {'color': 'yellow'}},
                          'right': {'type': 'leaf', 'color': 'red'}}, model.to_primitive())
        model.right = Branch({'leaf': {}})
        self.assertEqual({'left': {'type': 'branch', 'leaf': {'color': 'yellow'}},
                          'right': {'type': 'branch', 'leaf': {'color': 'green'}}}, model.to_primitive())
        with self.assertRaises(ValidationError) as ctx:
            model.validate()
        self.assertEqual({'right': ['Trees cannot have green leaves on the right side']}, ctx.exception.errors)

    def test_bad_configuration_not_union(self):
        class Bad(Model):
            field: Union[Leaf, None] = DynamicModelField(hide_none=True)

        with self.assertRaises(ConfigurationError) as ctx:
            Bad()
        self.assertEqual("Field field: DynamicModelField cannot be used for annotation Leaf, should use ModelField",
                         str(ctx.exception))

    def test_bad_configuration_non_model(self):
        class Bad(Model):
            field: Union[Leaf, Fake]

        with self.assertRaises(ConfigurationError) as ctx:
            Bad()
        self.assertEqual('Field field: Union Model fields can only be Optional or Union of Model subclass types, '
                         'got typing.Union[tests.common.Leaf, tests.test_model_fields.Fake]', str(ctx.exception))

    def test_bad_configuration_no_type(self):
        class Worse(Model):
            field: Union[Leaf, Trunk, None]

        with self.assertRaises(ConfigurationError) as ctx:
            Worse()
        self.assertEqual('Field field: Model Trunk used in a dynamic model field '
                         'typing.Union[tests.common.Leaf, tests.test_model_fields.Trunk] '
                         'but does not define a non-type-annotated string `type` field', str(ctx.exception))

    def test_bad_configuration_type_is_a_field(self):
        class Weird(Model):
            type: str = 'rogue annotation'

        class Horrible(Model):
            field: Union[Weird, Leaf]

            @classmethod
            def resolve_extra_types(cls) -> Set[Type[Model]]:
                return {Weird}

        with self.assertRaises(ConfigurationError) as ctx:
            Horrible()
        self.assertEqual(
            "Field field: Model Weird used in a dynamic model field "
            "typing.Union[tests.test_model_fields.TestDynamicModelField.test_bad_configuration_type_is_a_field."
            "<locals>.Weird, tests.common.Leaf] "
            "but its `type` field has a type annotation making it a field, must be an attribute",
            str(ctx.exception),
        )

    def test_bad_configuration_type_not_a_string(self):
        class Nonsense(Model):
            type = 5

        class Atrocity(Model):
            field: Union[Branch, Nonsense]

            @classmethod
            def resolve_extra_types(cls) -> Set[Type[Model]]:
                return {Branch, Nonsense, Leaf}

        with self.assertRaises(ConfigurationError) as ctx:
            Atrocity()
        self.assertEqual("Field field: Model Nonsense used in a dynamic model field "
                         "typing.Union[tests.test_model_fields.Branch, tests.test_model_fields.TestDynamicModelField."
                         "test_bad_configuration_type_not_a_string.<locals>.Nonsense] "
                         "but its `type` field 5 is not a string", str(ctx.exception))

    def test_bad_configuration_type_conflict(self):
        class AnotherLeaf(Leaf):
            pass

        class CrimeAgainstHumanity(Model):
            field: Union[Leaf, Branch, AnotherLeaf]

            @classmethod
            def resolve_extra_types(cls) -> Set[Type[Model]]:
                return {AnotherLeaf}

        with self.assertRaises(ConfigurationError) as ctx:
            CrimeAgainstHumanity()
        self.assertEqual("Field field: Conflicting dynamic model field types in typing.Union["
                         "tests.common.Leaf, tests.test_model_fields.Branch, tests.test_model_fields."
                         "TestDynamicModelField.test_bad_configuration_type_conflict.<locals>.AnotherLeaf"
                         "]: Leaf vs AnotherLeaf", str(ctx.exception))

    def test_bad_value(self):
        class Dynamic(Model):
            field: Union[Leaf, Branch]

        with self.assertRaises(ConversionError) as ctx:
            Dynamic({'field': Root({'depth': 1})})
        self.assertEqual('field: Expected Union[Leaf, Branch], got Root', str(ctx.exception))

        with self.assertRaises(ConversionError) as ctx:
            Dynamic({'field': []})
        self.assertEqual('field: Expected a mapping with a `type` field, got type list', str(ctx.exception))

        with self.assertRaises(ConversionError) as ctx:
            Dynamic({'field': {'color': 'no type'}})
        self.assertEqual('field: Expected a mapping with a `type` field, got no `type` field', str(ctx.exception))

        with self.assertRaises(ConversionError) as ctx:
            Dynamic({'field': {'type': 'nest', 'color': 'no type'}})
        self.assertEqual("field: Got a mapping with unsupported `type` 'nest'", str(ctx.exception))

        with self.assertRaises(ValidationError) as ctx:
            Dynamic().validate()
        self.assertEqual('field: This field is required', str(ctx.exception))

        with self.assertRaises(ValidationError) as ctx:
            Dynamic({'field': None}).validate()
        self.assertEqual('field: This field is required', str(ctx.exception))
