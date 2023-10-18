from __future__ import annotations

import dataclasses
from typing import List, Optional

from stereotype import Model, StrField, ListField
from bench.common import benchmark_cpu, memory_bench


@dataclasses.dataclass
class BaseStuff:
    name: str
    flag: bool = dataclasses.field(default=False)


@dataclasses.dataclass
class ListStuff(BaseStuff):
    stuff: Stuff = dataclasses.field(default=None)
    list: List[str] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        self.stuff = Stuff(**self.stuff)


@dataclasses.dataclass
class ModelStuff:
    value: float
    def_value: float = dataclasses.field(default=4.2)


@dataclasses.dataclass
class Stuff(BaseStuff):
    model: ModelStuff = dataclasses.field(default=None)
    optional: Optional[int] = dataclasses.field(default=None)
    strange: Optional[float] = dataclasses.field(default=4.7)
    items: List[ListStuff] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        self.model = ModelStuff(**self.model)
        self.items = [ListStuff(**item) for item in self.items]


if __name__ == '__main__':
    def benchmark(inputs: List[dict], validate: bool):
        for data in inputs:
            model = Stuff(**data)
            yield dataclasses.asdict(model)

    benchmark_cpu(benchmark, depth=4, validate=False)
    # memory_bench(lambda data: Stuff(**data), lambda model: dataclasses.asdict(model), 10, 4)  # 349MB
    # memory_bench(lambda data: data, lambda model: model, 10000, 4)  # 349MB
