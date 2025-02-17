from __future__ import annotations

from typing import Optional, Iterable
from unittest import TestCase, mock, skipIf

import schematics
from schematics.models import Model as SchematicsModel
from schematics.transforms import blacklist, whitelist
from schematics.types import IntType, StringType, FloatType, BooleanType
from schematics.types.compound import ModelType, ListType

from stereotype import (
    Model,
    StrField,
    Missing,
    Role,
    ValidationError,
    RequestedRoleFields,
    ConfigurationError,
    ConversionError,
)
from stereotype.contrib.schematics import SchematicsModelField


ROLE_X = Role("x")
ROLE_Y = Role("y")


class Inner(SchematicsModel):
    stuff = ListType(
        FloatType(required=True, max_value=7.0), required=True, default=list, max_size=2
    )
    bool = BooleanType(required=True)

    def to_primitive(self, role=None, context=None):
        data = super().to_primitive(role, context)
        if context is not None and context.get("private", False):
            data["stuff"] = "<hidden>"
        return data

    def __deepcopy__(self, memodict=None):
        # Works around the fact that deep copy doesn't work in Schematics 2
        return self.__class__(self.to_primitive())

    def __repr__(self):
        return "<Inner>"

    class Options:
        roles = {
            ROLE_X.name: blacklist("stuff"),
            ROLE_Y.name: whitelist("stuff"),
        }


class Root(Model):
    number: float = 42.0
    string: str = StrField(min_length=3)
    inner: Inner = SchematicsModelField(default=Inner)
    outer: Optional[Outer] = SchematicsModelField(
        hide_none=True, primitive_name="otter"
    )

    @classmethod
    def declare_roles(cls) -> Iterable[RequestedRoleFields]:
        yield ROLE_X.blacklist(cls.number)


class Outer(SchematicsModel):
    integer = IntType(required=True)
    string = StringType(required=False, default="def", choices=["str", "ing"])
    recursive = ModelType(Inner)

    @staticmethod
    def validate_integer(value, _):
        if value % 2:
            raise ValueError("Must be even")

    def __deepcopy__(self, memodict=None):
        # Works around the fact that deep copy doesn't work in Schematics 2
        return self.__class__(self.to_primitive())

    class Options:
        roles = {
            ROLE_X.name: blacklist(),
            ROLE_Y.name: whitelist("integer", "recursive"),
        }


class TestSchematicsModelField(TestCase):
    def test_empty(self):
        root = Root()
        self.assertEqual(Inner(), root.inner)
        self.assertIs(Missing, root.outer)
        self.assertEqual(
            {"inner": {"bool": None, "stuff": []}, "number": 42.0}, root.serialize()
        )
        self.assertEqual(root.copy(deep=True), root)
        self.assertEqual(
            "<Root {number=42.0, string=Missing, inner=<Inner>, outer=Missing}>",
            repr(root),
        )

    def test_none_value(self):
        root = Root({"inner": None, "otter": None})
        self.assertIsNone(root.inner)
        self.assertIsNone(root.outer)
        self.assertEqual({"inner": None, "number": 42.0}, root.serialize())
        self.assertEqual(root.copy(deep=True), root)
        with self.assertRaises(ValidationError) as e:
            root.validate()
        self.assertEqual(
            {
                "inner": ["This field is required"],
                "string": ["This field is required"],
            },
            e.exception.errors,
        )

    def test_full(self):
        root = Root(
            {
                "number": 47,
                "string": False,
                "inner": {"stuff": [1, 2, 3], "bool": 1},
                "otter": {
                    "integer": "7",
                    "string": 1,
                    "recursive": {"stuff": [1.0, 2.0, 3.0]},
                },
            }
        )
        self.assertEqual(Inner({"stuff": [1, 2, 3], "bool": True}), root.inner)
        self.assertEqual("1", root.outer.string)
        self.assertEqual(
            {
                "number": 47.0,
                "string": "False",
                "inner": {"stuff": [1.0, 2.0, 3.0], "bool": True},
                "otter": {
                    "integer": 7,
                    "string": "1",
                    "recursive": {"stuff": [1.0, 2.0, 3.0], "bool": None},
                },
            },
            root.to_primitive(),
        )

        copied = root.copy(deep=True)
        self.assertEqual(root, copied)
        copied.string = "True"
        self.assertNotEqual(root, copied)
        self.assertEqual(
            {
                "string": "True",
                "inner": {"bool": True},
                "otter": {"integer": 7, "string": "1", "recursive": {"bool": None}},
            },
            copied.serialize(role=ROLE_X),
        )
        self.assertEqual(
            {
                "number": 47.0,
                "string": "True",
                "inner": {"stuff": [1.0, 2.0, 3.0]},
                "otter": {"integer": 7, "recursive": {"stuff": [1.0, 2.0, 3.0]}},
            },
            copied.to_primitive(role=ROLE_Y),
        )

        with self.assertRaises(ValidationError) as e:
            root.validate()
        self.assertEqual(
            {
                "inner": {"stuff": ["Please provide no more than 2 items."]},
                "otter": {
                    "recursive": {
                        "bool": ["This field is required."],
                        "stuff": ["Please provide no more than 2 items."],
                    },
                    "string": [mock.ANY],
                },
            },
            e.exception.errors,
        )
        self.assertIn(
            "must be one of", e.exception.errors["otter"]["string"][0]
        )  # Exact message differs by version

    @skipIf(
        schematics.__version__ < "2",
        "Schematics 1 reporting of list item errors is broken",
    )
    def test_list_index_error_key(self):
        root = Root(
            {
                "string": "abc",
                "inner": {"stuff": [1, 9], "bool": True},
                "otter": None,
            }
        )
        with self.assertRaises(ValidationError) as e:
            root.validate()
        self.assertEqual(
            "inner: stuff: 1: Float value should be less than or equal to 7.0.",
            str(e.exception),
        )
        self.assertEqual(
            {
                "inner": {
                    "stuff": {"1": ["Float value should be less than or equal to 7.0."]}
                }
            },
            e.exception.errors,
        )

    def test_configuration_error_no_explicit_field(self):
        class Bad(Model):
            worse: Outer = Outer

        with self.assertRaises(ConfigurationError) as e:
            Bad()
        self.assertEqual(
            "Field worse of Bad: Unrecognized field annotation Outer (may need an explicit Field)",
            str(e.exception),
        )

    def test_configuration_error_mismatch(self):
        class Bad(Model):
            worse: Root = SchematicsModelField()

        with self.assertRaises(ConfigurationError) as e:
            Bad()
        self.assertEqual(
            "Field worse of Bad: SchematicsModelField cannot be used for annotation Root, "
            "should use ModelField",
            str(e.exception),
        )

    def test_to_primitive_context(self):
        root = Root(
            {
                "number": 47,
                "string": False,
                "inner": {"stuff": [1, 2, 3], "bool": 1},
                "otter": {
                    "integer": "7",
                    "string": 1,
                    "recursive": {"stuff": [1.0, 2.0, 3.0]},
                },
            }
        )
        primitive_value = root.to_primitive(context={"private": True})
        self.assertEqual(primitive_value["inner"]["stuff"], "<hidden>")

    def test_conversion_error_from_schematics(self):
        with self.assertRaises(ConversionError) as ctx:
            Root({"inner": {"bool": ""}})

        self.assertEqual(
            {"inner": {"bool": ["Must be either true or false."]}},
            ctx.exception.errors,
        )

    def test_conversion_error_from_schematics_deep(self):
        with self.assertRaises(ConversionError) as ctx:
            Root(
                {
                    "number": 47,
                    "string": False,
                    "inner": {"stuff": [1, 2, 3], "bool": 1},
                    "otter": {
                        "integer": "7",
                        "string": 1,
                        "recursive": {"stuff": [1.0, 2.0, 3.0], "bool": ""},
                    },
                }
            )
        self.assertEqual(
            {"otter": {"recursive": {"bool": ["Must be either true or false."]}}},
            ctx.exception.errors,
        )
