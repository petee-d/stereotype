from __future__ import annotations

from threading import Lock
from typing import List, Set, Optional

from supermodel.utils import ConfigurationError


class Role:
    __slots__ = ('code', 'name', 'empty_by_default')

    def __init__(self, name: str, empty_by_default: bool = False):
        self.name = name
        self.empty_by_default = empty_by_default
        with _roles_lock:
            self.code = len(_roles)
            _roles.append(self)

    def __repr__(self):
        return f'<Role {self.name}, empty_by_default={self.empty_by_default}, code={self.code}>'

    def __hash__(self):
        return self.code

    def __eq__(self, other):
        return type(self) == type(other) and self.code == other.code

    def whitelist(self, *fields, override_parents: bool = False):
        return RequestedRoleFields(self, fields, is_whitelist=True, override_parents=override_parents)

    def blacklist(self, *fields, override_parents: bool = False):
        return RequestedRoleFields(self, fields, is_whitelist=False, override_parents=override_parents)


_roles: List[Role] = []
_roles_lock = Lock()


class FinalizedRoleFields:
    __slots__ = ('role', 'fields')

    def __init__(self, role: Role, fields: Optional[Set[str]] = None):
        self.role = role
        self.fields = fields or set()

    def update_requested(self, other: RequestedRoleFields, all_field_names: Set[str], field_names: Set[str]):
        assert self.role == other.role
        if other.override_parents:
            initial = set() if other.is_whitelist else all_field_names
        else:
            initial = self.fields
        if other.is_whitelist:
            self.fields = initial | other.fields
        else:
            self.fields = (initial | field_names) - other.fields


class RequestedRoleFields:
    __slots__ = ('role', 'fields', 'is_whitelist', 'override_parents')

    def __init__(self, role: Role, fields, is_whitelist: bool, override_parents: bool):
        non_descriptors = [field for field in fields if type(field).__name__ != 'member_descriptor']
        if non_descriptors:
            raise ConfigurationError(f'Role blacklist/whitelist needs member descriptors (e.g. cls.my_field), '
                                     f'got {non_descriptors[0]!r}')
        self.role = role
        self.fields: Set[str] = {field.__name__ for field in fields}
        self.is_whitelist = is_whitelist
        self.override_parents = override_parents
