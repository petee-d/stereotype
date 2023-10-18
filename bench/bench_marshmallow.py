from typing import List

from marshmallow import Schema, fields, validate, validates_schema, ValidationError

from bench.common import memory_bench, benchmark_cpu


class BaseStuff(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1))
    flag = fields.Bool(load_default=False)


class ListStuff(BaseStuff):
    stuff = fields.Nested(lambda: Stuff(), required=True)
    list = fields.List(fields.Str(required=True), required=True, min_size=1)


class ModelStuff(Schema):
    value = fields.Float(required=True)
    def_value = fields.Float(required=False, load_default=4.2)


class Stuff(BaseStuff):
    optional = fields.Int(required=False, load_default=None)
    strange = fields.Float(required=False, load_default=4.7)
    model = fields.Nested(ModelStuff, required=True)
    items = fields.List(fields.Nested(ListStuff, required=True), load_default=list)

    @validates_schema
    def validate_flag(self, data, partial, many):
        if not data['flag'] and data['optional'] is None:
            raise ValidationError('Must be true if optional is not set')


schema = Stuff()


if __name__ == '__main__':
    def benchmark(inputs: List[dict], validate: bool):
        for data in inputs:
            model = schema.load(data)
            if validate:
                model.validate()
            yield model.serialize()

    benchmark_cpu(benchmark, depth=4, validate=True)
    # memory_bench(Stuff, lambda model: model.to_primitive(), 10000, 4)
