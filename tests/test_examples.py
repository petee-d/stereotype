from unittest import TestCase


class TestExamples(TestCase):
    def test_flat(self):
        from examples.flat import Employee
        Employee()
