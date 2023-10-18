from __future__ import annotations

from typing import List, Optional

from stereotype import Model, StrField, ListField
from bench.common import benchmark_cpu, memory_bench


class BaseStuff(Model):
    __abstract__ = True

    name: str = StrField(min_length=2)
    flag: bool = False


class ListStuff(BaseStuff):
    stuff: Stuff
    list: List[str] = ListField(min_length=1)


class ModelStuff(Model):
    value: float
    def_value: float = 4.2


class Stuff(BaseStuff):
    optional: Optional[int] = None
    strange: Optional[float] = 4.7
    model: ModelStuff
    items: List[ListStuff] = list

    def validate_flag(self, value: bool, _):
        if not value and self.optional is None:
            raise ValueError('Must be true if optional is not set')


if __name__ == '__main__':
    def benchmark(inputs: List[dict], validate: bool):  # 87.6
        # model = Stuff(inputs[0])
        for data in inputs:
            # model.validate()
            # continue
            model = Stuff(data)  # 0.583 -> 0.279
            if validate:
                model.validate()  # 0.334 -> 0.299
            yield model.to_primitive()  # 0.270


    benchmark_cpu(benchmark, depth=4, validate=True)
    # memory_bench(Stuff, lambda model: model.to_primitive(), 10000, 4)  # 349MB
