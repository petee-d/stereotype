from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, validator
from bench.common import execute, benchmark_cpu, memory_bench


class BaseStuff(BaseModel):
    name: str
    flag: bool = False

    @validator('name')
    def name_min_length_2(cls, v):
        if len(v) < 2:
            raise ValueError('must be at least 2 characters long')
        return v


class ListStuff(BaseStuff):
    stuff: Stuff
    list: List[str]

    @validator('list')
    def list_min_length_1(cls, v):
        if len(v) < 1:
            raise ValueError('must have at least 1 items')
        return v


class ModelStuff(BaseModel):
    value: float
    def_value: float = 4.2


class Stuff(BaseStuff):
    optional: Optional[int]
    strange: Optional[float] = 4.7
    model: ModelStuff
    items: List[ListStuff]

    @validator('flag', 'optional')
    def flag_set_if_not_optional(cls, flag, values):
        if not flag and values.get('optional') is None:
            raise ValueError('Must be true if optional is not set')
        return flag


ListStuff.update_forward_refs()


if __name__ == '__main__':
    def benchmark(inputs: List[dict], validate: bool):
        for data in inputs:
            if validate:
                model = Stuff(**data)
            else:
                model = Stuff.construct(**data)
            yield model.dict()

    benchmark_cpu(benchmark, depth=4, validate=False)
    # memory_bench(lambda data: Stuff(**data), lambda model: model.dict(), 10000, 4)  # 651 MB
