from unittest import TestCase


class TestExamples(TestCase):
    def test_flat(self):
        from supermodel.examples.flat import Employee
        Employee()
