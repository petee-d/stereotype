from stereotype import Model, StrField, DEFAULT_ROLE


class Leaf(Model):
    type = 'leaf'

    color: str = 'green'


class PrivateStrField(StrField):
    def to_primitive(self, value, role=DEFAULT_ROLE, context=None):
        if context is not None and context.get('private', False):
            return '<hidden>'
        return value
