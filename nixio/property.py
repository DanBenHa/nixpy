# -*- coding: utf-8 -*-
# Copyright © 2014, German Neuroinformatics Node (G-Node)
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted under the terms of the BSD License. See
# LICENSE file in the root of the Project.

from collections import Sequence
from enum import Enum
import numpy as np

from .datatype import DataType
from .entity import Entity
from . import util


class OdmlType(str, Enum):
    """
    OdmlType provides all types currently supported by the odML
    data format. It provides additional information about the
    nature of the values of an odML Property.
    """
    boolean = 'boolean'
    int = 'int'
    float = 'float'
    string = 'string'
    text = 'text'
    url = 'url'
    person = 'person'
    datetime = 'datetime'
    date = 'date'
    time = 'time'

    def __str__(self):
        return self.name

    def compatible(self, value):
        """
        compatible returns True or False dependent on whether a
        passed in value can be mapped to an OdmlType or not.

        :param value: Any single value
        :return: Boolean
        """
        if (self.name in ("string", "text", "url", "person") and
                DataType.get_dtype(value) == DataType.String):
            return True
        elif self.name == "boolean" and DataType.get_dtype(value) == DataType.Bool:
            return True
        elif self.name == "float" and DataType.get_dtype(value) == DataType.Float:
            return True
        elif self.name == "int" and DataType.get_dtype(value) == DataType.Int64:
            return True
        elif (self.name in ("time", "date", "datetime") and
              DataType.get_dtype(value) == DataType.String):
            # This might need some extra work, treating as String for now, but keeping
            # it separated from other String values.
            return True

        return False

    @staticmethod
    def get_odml_type(dtype):
        """
        get_odml_type returns the appropriate OdmlType
        for a handed in nix value DataType.

        :param dtype: nix DataType
        :return: OdmlType
        """

        if dtype == DataType.Float:
            return OdmlType.float
        elif dtype == DataType.Int64:
            return OdmlType.int
        elif dtype == DataType.String:
            return OdmlType.string
        elif dtype == DataType.Bool:
            return OdmlType.boolean

        raise TypeError("No available OdmlType for type '%s'" % dtype)


class Property(Entity):
    """An odML Property"""
    def __init__(self, nixparent, h5dataset):
        super(Property, self).__init__(nixparent, h5dataset)
        self._h5dataset = self._h5group

    @classmethod
    def _create_new(cls, nixparent, h5parent, name, dtype, oid=None):
        util.check_entity_name(name)
        dtype = cls._make_h5_dtype(dtype)

        h5dataset = h5parent.create_dataset(name, shape=(0,), dtype=dtype)
        h5dataset.set_attr("name", name)

        if not util.is_uuid(oid):
            oid = util.create_id()

        h5dataset.set_attr("entity_id", oid)

        newentity = cls(nixparent, h5dataset)
        newentity.force_created_at()
        newentity.force_updated_at()

        return newentity

    @property
    def name(self):
        return self._h5dataset.get_attr("name")

    @property
    def definition(self):
        return self._h5dataset.get_attr("definition")

    @definition.setter
    def definition(self, d):
        util.check_attr_type(d, str)
        self._h5dataset.set_attr("definition", d)

    @property
    def unit(self):
        return self._h5dataset.get_attr("unit")

    @unit.setter
    def unit(self, new):
        if new:
            new = util.units.sanitizer(new)

        if new == "":
            new = None

        util.check_attr_type(new, str)
        self._h5dataset.set_attr("unit", new)

    @property
    def uncertainty(self):
        return self._h5dataset.get_attr("uncertainty")

    @uncertainty.setter
    def uncertainty(self, uncertainty):
        # Use int as type check for now but check whether
        # it should be changed to float.
        util.check_attr_type(uncertainty, int)
        self._h5dataset.set_attr("uncertainty", uncertainty)

    @property
    def reference(self):
        return self._h5dataset.get_attr("reference")

    @reference.setter
    def reference(self, ref):
        util.check_attr_type(ref, str)
        self._h5dataset.set_attr("reference", ref)

    @property
    def dependency(self):
        return self._h5dataset.get_attr("dependency")

    @dependency.setter
    def dependency(self, dep):
        util.check_attr_type(dep, str)
        self._h5dataset.set_attr("dependency", dep)

    @property
    def dependency_value(self):
        return self._h5dataset.get_attr("dependency_value")

    @dependency_value.setter
    def dependency_value(self, depval):
        util.check_attr_type(depval, str)
        self._h5dataset.set_attr("dependency_value", depval)

    @property
    def value_origin(self):
        return self._h5dataset.get_attr("value_origin")

    @value_origin.setter
    def value_origin(self, origin):
        util.check_attr_type(origin, str)
        self._h5dataset.set_attr("value_origin", origin)

    @property
    def odml_type(self):
        otype = self._h5dataset.get_attr("odml_type")
        if not otype:
            return None

        return OdmlType(otype)

    @odml_type.setter
    def odml_type(self, new_type):
        """
        odml_type can only be set if the handed in new type is a valid
        OdmlType and if it is compatible with the value data type of
        the property.

        :param new_type: OdmlType
        """
        if not isinstance(new_type, OdmlType):
            raise TypeError("'%s' is not a valid odml_type." % new_type)

        if not new_type.compatible(self.values[0]):
            raise TypeError("Type '%s' is incompatible with property values" % new_type)

        self._h5dataset.set_attr("odml_type", str(new_type))

    @property
    def values(self):
        dataset = self._h5dataset
        if not sum(dataset.shape):
            return tuple()

        data = dataset.read_data()

        def data_to_value(dat):
            if isinstance(dat, bytes):
                dat = dat.decode()
            return dat

        values = tuple(map(data_to_value, data))

        return values

    @values.setter
    def values(self, vals):
        """
        Set the value of the property discarding any previous information.

        :param vals: a single value or list of values.
        """
        # Make sure boolean value 'False' gets through as well...
        if vals is None or (isinstance(vals, Sequence) and not vals):
            self.delete_values()
            return

        # Make sure all values are of the same data type
        single_val = vals
        if isinstance(vals, Sequence):
            single_val = vals[0]

        # Will raise an error, if the data type of the first value is not valid.
        vtype = DataType.get_dtype(single_val)

        # Check if the data type has changed and raise an exception otherwise.
        if vtype != self.data_type:
            raise TypeError("New data type '%s' is inconsistent with the "
                            "Properties data type '%s'" % (vtype, self.data_type))

        # Check all values for data type consistency to ensure clean value add.
        # Will raise an exception otherwise.
        for val in vals:
            if DataType.get_dtype(val) != vtype:
                raise TypeError("Array contains inconsistent values. Only values of "
                                "type '%s' can be assigned" % vtype)

        self._h5dataset.shape = np.shape(vals)

        data = np.array(vals, dtype=vtype)

        self._h5dataset.write_data(data)

    @property
    def data_type(self):
        dtype = self._h5dataset.dtype

        if dtype == util.vlen_str_dtype:
            return DataType.String

        return dtype

    def delete_values(self):
        self._h5dataset.shape = (0,)

    @staticmethod
    def _make_h5_dtype(valued_type):
        str_ = util.vlen_str_dtype

        if valued_type == DataType.String:
            valued_type = str_

        return valued_type

    def __str__(self):
        return "{}: {{name = {}}}".format(
            type(self).__name__, self.name
        )

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if hasattr(other, "id"):
            return self.id == other.id

        return False

    def __hash__(self):
        """
        overwriting method __eq__ blocks inheritance of __hash__ in Python 3
        hash has to be either explicitly inherited from parent class,
        implemented or escaped
        """
        return hash(self.id)
