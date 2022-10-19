# This file should have no `from __future__ import annotations` to improve coverage of some cases
from typing import ClassVar
from unittest import TestCase

import typing

from stereotype import Model


class TestRawAnnotations(TestCase):
    def test_class_var(self):
        class HasClassVar(Model):
            normal_field: int = 1
            # ClassVar attributes shouldn't become fields
            class_var_1: ClassVar[int] = 2
            class_var_2: "ClassVar[float]" = 3.0
            class_var_3: "typing.ClassVar[typing.List[str]]" = ["4"]

            @classmethod
            def class_var_sum(cls):
                return cls.class_var_1 + cls.class_var_2

        model = HasClassVar({"class_var": "ignore me"})
        self.assertEqual(1, model.normal_field)
        self.assertEqual(2, model.class_var_1)
        self.assertEqual(3.0, model.class_var_2)
        self.assertEqual(5.0, model.class_var_sum())
        self.assertEqual(["4"], model.class_var_3)
        self.assertEqual(2, HasClassVar.class_var_1)
        self.assertEqual(3.0, HasClassVar.class_var_2)
        self.assertEqual(5.0, HasClassVar.class_var_sum())
        self.assertEqual(["4"], HasClassVar.class_var_3)
        self.assertEqual({"normal_field": 1}, model.serialize())
