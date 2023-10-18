import gc
import json
from time import sleep, time
from typing import Callable, List, Iterable


def make_stuff_data(items: int):
    return {
        'name': 'xyz',
        'flag': True,
        'model': {'value': 42},
        'items': [{
            'name': 'abc',
            'stuff': make_stuff_data(items - 1),
            'list': [str(i) for i in range(items)],
        } for _ in range(items)],
    }


def benchmark_cpu(executable: Callable[[List[dict], bool], Iterable[dict]], depth: int = 2, validate: bool = False):
    iterations = 10
    target_seconds = 1.0

    # Execute once just to initialize the classes
    list(executable([make_stuff_data(depth)], validate))

    # Execute 10 times to get an initial estimate to make the run time close to target INCLUDING making the data
    start = float(time())
    data = [make_stuff_data(depth) for _ in range(10)]
    for _ in executable(data, validate):
        pass
    print(time(), start)
    estimate = (time() - start) / 10

    n = round(target_seconds / estimate)
    print(f'Iterations: {n}, time reported in milliseconds:')

    best = float('inf')
    for i in range(iterations):
        data = [make_stuff_data(depth)] * n  # [make_stuff_data(depth) for _ in range(n)]
        start = time()
        for _ in executable(data, validate):
            pass
        milliseconds = 1e3 * (time() - start) / n
        best = min(best, milliseconds)
        print(f'Run {i}: {milliseconds:.3f}')

    print(f'Ideal: {best:.3f}')


def execute(model, iterations, depth):
    stuff = model(make_stuff_data(1))
    print(stuff)
    try:
        stuff.xyz = 'Slots restricted: NO'
        print(stuff.xyz)
    except (AttributeError, ValueError):
        print('Slots restricted: YES')
    stuff_serialized = json.dumps(stuff.serialize())
    #print(len(stuff_serialized))
    #print(stuff_serialized)

    serialized = make_stuff_data(depth)
    data = [make_stuff_data(depth) for i in range(iterations)]
    objects = [None] * iterations
    started = time()
    for i in range(iterations):
        stuff = model(data[i])
        serialized = stuff.serialize()
        #stuff.validate()
        objects[i] = stuff
        data[i] = None
    ended = time()
    print(f'{(ended - started) / max(iterations, 1):0.9f}')
    #print(len(json.dumps(serialized)))
    #print(type(objects))


def memory_bench(model, serialize, iterations, depth):
    import os
    import psutil

    process = psutil.Process(os.getpid())
    json_data = json.dumps(serialize(model(make_stuff_data(depth))))
    print(len(json_data))
    started = time()
    # initial = make_stuff_data(depth)
    objects = [model(make_stuff_data(depth)) for i in range(iterations)]
    ended = time()
    print(f'{(ended - started) / max(iterations, 1):0.9f}')
    print(type(objects))
    gc.collect()
    sleep(2)

    print(mem_start := process.memory_info().rss)
    del objects
    gc.collect()
    sleep(2)
    print(mem_end := process.memory_info().rss)
    print((mem_start - mem_end) / iterations)
