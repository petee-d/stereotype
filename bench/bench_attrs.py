from __future__ import annotations

from typing import List, Optional

from attrs import define, field, asdict, validators
from bench.common import execute, benchmark_cpu, memory_bench


@define(slots=True)
class BaseStuff:
    name: str = field(converter=str)
    flag: bool = field(converter=bool, default=False)

    @name.validator
    def name_min_length_2(self, attribute, v):
        if len(v) < 2:
            raise ValueError('must be at least 2 characters long')


@define(slots=True)
class ListStuff(BaseStuff):
    stuff: Stuff = field(converter=lambda data: Stuff(**data), default=None)
    list: List[str] = field(converter=lambda items: [str(item) for item in items], default=list)

    @list.validator
    def list_min_length_1(self, attribute, v):
        if len(v) < 1:
            raise ValueError('must have at least 1 items')


@define(slots=True)
class ModelStuff:
    value: float = field(converter=float)
    def_value: float = field(converter=float, default=4.2)


@define(slots=True)
class Stuff(BaseStuff):
    model: ModelStuff = field(converter=lambda data: ModelStuff(**data), default=None)
    items: List[ListStuff] = field(converter=lambda data: [ListStuff(**item) for item in data], default=list)
    optional: Optional[int] = field(converter=lambda val: int(val) if val is not None else None, default=None)
    strange: Optional[float] = field(converter=lambda val: float(val) if val is not None else None, default=4.7)

    @optional.validator
    def flag_set_if_not_optional(self, attribute, optional):
        if not self.flag and optional is None:
            raise ValueError('Must be true if optional is not set')


if __name__ == '__main__':
    def benchmark(inputs: List[dict], validate: bool):
        # model = Stuff(**inputs[0])
        for data in inputs:
            if validate:
                model = Stuff(**data)
            else:
                with validators.disabled():
                    model = Stuff(**data)  # 0.335
            yield asdict(model)  # 0.830


    Stuff(name='test', items='')
    # benchmark_cpu(benchmark, depth=4, validate=False)
    # memory_bench(lambda data: Stuff(**data), lambda model: asdict(model), 10000, 4)  # 339MB
