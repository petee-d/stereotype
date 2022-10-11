Fields
======

Most fields are created simply with an annotated class attribute, with an optional default:

.. code-block:: python

    class MyModel(Model):
        required: int
        optional: Optional[str] = None

If you wish to use advanced field options, such as validation, assign an instance of one of these field classes
to the attribute. The type hint is still mandatory and should correspond to the type represented by the field class.

.. autoclass:: stereotype.BoolField
.. autoclass:: stereotype.IntField
.. autoclass:: stereotype.FloatField
.. autoclass:: stereotype.StrField
.. autoclass:: stereotype.ListField
.. autoclass:: stereotype.DictField
.. autoclass:: stereotype.ModelField
.. autoclass:: stereotype.DynamicModelField
.. autoclass:: stereotype.AnyField

serializable & SerializableField
--------------------------------
.. autofunction:: stereotype.serializable
.. autoclass:: stereotype.SerializableField
