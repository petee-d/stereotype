# Parts of this file are referenced from docs by line numbers, always update docs after changing it!

from __future__ import annotations
from typing import Optional, Any, Union, List
from stereotype import Model


class Variable(Model):
    name: str


class IsEqual(Model):
    type = 'equal'

    variable: Variable
    constant: Constant


class Constant(Model):
    value: Optional[Any] = None


equality = IsEqual({'variable': {'name': 'x'}, 'constant': {'value': 42}})
assert equality.variable.name == 'x'
assert equality.type == 'equal'
assert equality.to_primitive() == {'variable': {'name': 'x'}, 'constant': {'value': 42}}


class Negation(Model):
    type = 'not'

    formula: Union[IsEqual, Conjunction]


class Conjunction(Model):
    type = 'and'

    operands: List[Union[IsEqual, Negation, Conjunction]] = []


equality_copy = equality.copy(deep=True)
model = Conjunction({'operands': [
    {'type': 'not', 'formula': equality_copy},
    {'type': 'equal', 'variable': {'name': 'y'}, 'constant': {}},
]})
assert isinstance(model.operands[0], Negation)
assert model.operands[0].type == 'not'
assert model.to_primitive() == {'operands': [
    {'type': 'not', 'formula': {'type': 'equal', 'variable': {'name': 'x'}, 'constant': {'value': 42}}},
    {'type': 'equal', 'variable': {'name': 'y'}, 'constant': {'value': None}},
]}
