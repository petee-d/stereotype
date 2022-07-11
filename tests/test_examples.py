from unittest import TestCase


class TestExamples(TestCase):
    def test_atomic_fields(self):
        from examples.atomic_fields import Employee
        Employee()

    def test_compound_fields(self):
        from examples.compound_fields import Book
        Book()

    def test_model_fields(self):
        from examples.model_fields import Conjunction
        Conjunction()

    def test_schematics_field(self):
        from examples.schematics_field import Branch
        Branch()
