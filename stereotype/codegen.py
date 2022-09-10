from contextlib import contextmanager
from typing import Any


class CodeGenerator:
    __slots__ = ['_lines', '_globals', '_indent', '_scope_name']

    def __init__(self):
        self._lines = []
        self._globals = {}
        self._indent = 0
        self._scope_name = ''

    @contextmanager
    def indent(self):
        self._indent += 1
        yield
        self._indent -= 1

    @contextmanager
    def name_scope(self, name: str):
        old_scope_name = self._scope_name
        self._scope_name = f'{old_scope_name}{name}_'
        yield
        self._scope_name = old_scope_name

    def line(self, code: str):
        self._lines.append(self._indent * "    " + code)

    def declare_global(self, name: str, value: Any) -> str:
        assert name not in self._globals or self._globals[name] is value, 'Conflicting symbol declaration'
        self._globals[name] = value
        return name

    def declare_scoped_global(self, name_suffix: str, value: Any) -> str:
        return self.declare_global(self.scoped_name(name_suffix), value)

    def scoped_name(self, name_suffix: str) -> str:
        return self._scope_name + name_suffix

    def exec(self, symbol: str) -> Any:
        local_vars = {}
        # print()
        # print("\n".join(self._lines))
        # print(self._globals)
        code = "\n".join(self._lines)
        exec(code, self._globals, local_vars)
        return local_vars[symbol]
