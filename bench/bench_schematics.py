from typing import List

from schematics.exceptions import ValidationError
from schematics.models import Model
from schematics.types import StringType, BooleanType, IntType, FloatType
from schematics.types.compound import ListType, ModelType
from schematics.types.serializable import serializable

from bench.common import execute, benchmark_cpu, memory_bench


class DelayedModelType(ModelType):
    # noinspection PyMissingConstructor
    def __init__(self, model_class_callable, **kwargs):
        super(ModelType, self).__init__(**kwargs)
        super_init = super().__init__
        self.init = lambda: super_init(model_class_callable(), **kwargs)


DelayedStuffModelType = DelayedModelType(lambda: Stuff, required=True)


class BaseStuff(Model):
    name = StringType(required=True, min_length=2)
    flag = BooleanType(required=True, default=False)


class ListStuff(BaseStuff):
    stuff = DelayedStuffModelType
    list = ListType(StringType(required=True), required=True, min_size=1)


class ModelStuff(Model):
    value = FloatType(required=True)
    def_value = FloatType(required=False, default=4.2)


class Stuff(BaseStuff):
    optional = IntType(required=False, default=None)
    strange = FloatType(required=False, default=4.7)
    model = ModelType(ModelStuff, required=True)
    items = ListType(ModelType(ListStuff, required=True), required=True, default=list)

    def validate_flag(self, data, value):
        if not value and data['optional'] is None:
            raise ValidationError('Must be true if optional is not set')


DelayedStuffModelType.init()


# class SerializableTest(Model):
#     stuff = StringType()
#     stuff2 = StringType(serialized_name='stuff3')
#
#     @serializable
#     def other(self):
#         return self.stuff + ' ' + self.stuff
#
#
# print(list(SerializableTest({'stuff': 'abc', 'stuff2': 'abc'}).items()))
# print(SerializableTest({'stuff': 'abc', 'stuff3': 'xyz'}).serialize())


if __name__ == '__main__':
    def benchmark(inputs: List[dict], validate: bool):
        for data in inputs:
            model = Stuff(data)
            if validate:
                model.validate()
            yield model.to_primitive()

    benchmark_cpu(benchmark, depth=4, validate=False)
    # memory_bench(Stuff, lambda model: model.to_primitive(), 10000, 4)  # 1720 MB
