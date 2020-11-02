from typing import Optional

from supermodel import Model, FloatField


class Employee(Model):
    name: str
    department: str = 'Engineering'
    female: Optional[bool] = None
    salary: float = FloatField(min_value=42., default=42.)

    human = True

    def greeting(self) -> str:
        return f'Dear { {True: "Ms. ", False: "Mr. "}.get(self.female, "")}{self.name}'


model = Employee({'name': 'Jane Doe', 'female': True, 'salary': 150000})
model.validate()
assert model.name == 'Jane Doe'
assert model.department == 'Engineering'
assert model.female is True
assert model.salary == 150000.0
assert model.human is True
assert model.greeting() == 'Dear Ms. Jane Doe'
model.salary = 200000.0
primitive = model.to_primitive()
assert primitive == {'name': 'Jane Doe', 'department': 'Engineering', 'female': True, 'salary': 200000.0}


from supermodel import ValidationError, Missing  # noqa

model = Employee({'department': None, 'salary': '10'})
try:
    model.validate()
    assert False, 'Validation fails due to errors below'
except ValidationError as e:
    assert str(e) == 'name: This field is required'
    assert e.errors == {
        'name': ['This field is required'],
        'department': ['This field is required'],
        'salary': ['Must be at least 42.0'],
    }
assert model.name is Missing
assert model.department is None
assert model.salary == 10.0
assert model.to_primitive() == {'department': None, 'female': None, 'salary': 10.0}

from supermodel import ConversionError  # noqa

try:
    model = Employee({'name': 'Alien', 'female': 'Unknown'})
except ConversionError as e:
    assert str(e) == 'female: Value must be a boolean or a true/false/yes/no string value'
