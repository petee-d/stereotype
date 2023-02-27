from typing import Any, Optional
from unittest import TestCase

from stereotype import StrField, Missing, Role, DEFAULT_ROLE, Model


class PrefixStrField(StrField):
    """
    Converted data strips a prefix from primitive data.
    Demonstrates creating custom fields, especially with required parameters.
    """

    def __init__(self, prefix: str, **kwargs):
        super().__init__(**kwargs)
        self.prefix = prefix

    def convert(self, value: Any) -> Any:
        converted = super().convert(value)
        if value is None or value is Missing:
            return value
        return converted[len(self.prefix):] if converted.startswith(self.prefix) else value

    def to_primitive(self, value: Any, role: Role = DEFAULT_ROLE, context=None) -> Any:
        primitive = super().to_primitive(value, role, context)
        if value is None or value is Missing:
            return value
        return self.prefix + primitive


class TestCustomFields(TestCase):
    def test_prefix_str_field(self):
        class MyModel(Model):
            a_prefix: Optional[str] = PrefixStrField('a_')

        model = MyModel({"a_prefix": "a_value"})
        self.assertEqual("value", model.a_prefix)
        self.assertEqual({"a_prefix": "a_value"}, model.to_primitive())

        model = MyModel({"a_prefix": "value"})
        self.assertEqual("value", model.a_prefix)
        self.assertEqual({"a_prefix": "a_value"}, model.to_primitive())

        model = MyModel({"a_prefix": None})
        self.assertIsNone(model.a_prefix)
        self.assertEqual({"a_prefix": None}, model.to_primitive())

        model = MyModel({})
        self.assertIs(Missing, model.a_prefix)
        self.assertEqual({}, model.to_primitive())
