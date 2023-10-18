from __future__ import annotations

import re
from typing import Optional, Union

from stereotype import Model, FloatField


class BaseConstant(Model):
    comment: Optional[str] = None


class BoolConstant(BaseConstant):
    type = 'bool'

    value: bool = False


class StringConstant(BaseConstant):
    type = 'string'

    value: str

    value_regex = re.compile('^[a-zA-Z0-9_]+$')

    def validate_value(self, value: str, context: Optional[dict] = None):
        if not self.value_regex.match(value):
            raise ValueError('Can only contain alphanumeric characters, numbers or underscore, cannot be empty')


class NumberConstant(BaseConstant):
    type = 'number'

    value: float = FloatField(min_value=0.)


class Definition(Model):
    name: str
    attribute: Union[StringConstant, NumberConstant, BoolConstant]


def do_test():
    model = Definition({'name': 'abc', 'attribute': {'type': 'bool', 'value': '4.7'}})
    print(model)
    print(model.serialize())
    model.validate()


if __name__ == '__main__':
    do_test()
