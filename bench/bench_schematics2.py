from typing import List

from schematics.exceptions import ValidationError
from schematics.models import Model
from schematics.types import StringType, BooleanType, IntType, FloatType
from schematics.types.compound import ListType, ModelType

from bench.common import memory_bench, benchmark_cpu


class BaseStuff(Model):
    name = StringType(required=True, min_length=2)
    flag = BooleanType(required=True, default=False)


class ListStuff(BaseStuff):
    stuff = ModelType('bench.bench_schematics2.Stuff', required=True)
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


if __name__ == '__main__':
    def benchmark(inputs: List[dict], validate: bool):
        for data in inputs:
            model = Stuff(data)
            if validate:
                model.validate()
            yield model.serialize()

    benchmark_cpu(benchmark, depth=4, validate=True)
    # memory_bench(Stuff, lambda model: model.to_primitive(), 10000, 4)
