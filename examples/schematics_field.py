from __future__ import annotations

# Keep this file synchronized with the `stereotype/contrib/README.md` documentation!

from typing import Optional, List

from schematics.models import Model as SchematicsModel
from schematics.types import StringType, IntType

from stereotype import Model, ListField
from stereotype.contrib.schematics import SchematicsModelField


class Leaf(SchematicsModel):
    color: str = StringType(required=True, default="green")


class Fruit(SchematicsModel):
    worms: Optional[int] = IntType()


class Branch(Model):
    length: float
    fruit: Optional[Fruit] = SchematicsModelField(hide_none=True, default=None)
    leaves: List[Leaf] = ListField(SchematicsModelField(), max_length=50)


branch = Branch({'length': 42, 'leaves': [{'color': 'yellow'}, {}]})
assert branch.leaves[1].color == 'green'
assert branch.fruit is None
assert branch.serialize() == {'length': 42, 'leaves': [{'color': 'yellow'}, {'color': 'green'}]}

branch.fruit = Fruit({'worms': 2})
assert branch.serialize()['fruit'] == {'worms': 2}
branch.validate()
