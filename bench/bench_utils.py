from random import random
from time import time
from typing import Callable, Any

from stereotype import BoolField


def bench(n: int, executable: Callable[[], Any]):
    started = time()
    for i in range(n):
        executable()
    ended = time()
    print(f'{executable} {(ended - started) / n:.9f}')


_stuff = []


def my_exception_func():
    if random() < 0.001:
        raise ValueError('abc')


def bench_exceptions():
    try:
        my_exception_func()
        return ''
    except ValueError as e:
        return str(e)


def my_iter_error_func():
    if random() < 0.001:
        yield 'abc'


def bench_iter_errors():
    for error in my_iter_error_func():
        return error
    return ''


def my_return_error_func():
    if random() < 0.001:
        return 'abc'
    return None


def bench_return_errors():
    result = my_return_error_func()
    if result is not None:
        return result
    return ''


def bench_getattr_normal():
    (getattr(_stuff, 'append'))


def bench_getattr_internal():
    (_stuff.__getattribute__('append'))


_model = BoolField()
_x = True


def bench_globally_imported_symbol():
    return isinstance(_model, BoolField)


def bench_locally_imported_symbol():
    from stereotype.fields import Field
    return isinstance(_model, Field)


def bench_isinstance_bool():
    global _x
    x = True
    for i in range(1000):
        x = x and isinstance(_x, bool)
    _x = x
    return x


def bench_is_true_false():
    global _x
    x = True
    for i in range(1000):
        x = x and _x is False or _x is True
    _x = x
    return x


def bench_try_inside():
    for i in range(1000):
        try:
            if random()*i > 990:
                raise ValueError('abc')
        except ValueError:
            return i


def bench_try_outside():
    try:
        for i in range(1000):
            if random()*i > 990:
                raise ValueError('abc')
    except ValueError:
        return 999


# bench(1000000, bench_exceptions)
# bench(1000000, bench_iter_errors)
# bench(1000000, bench_return_errors)

# bench(10000000, bench_getattr_normal)
# bench(10000000, bench_getattr_internal)

# bench(10000, bench_isinstance_bool)
# bench(10000, bench_is_true_false)

bench(10000, bench_try_inside)
bench(10000, bench_try_outside)
