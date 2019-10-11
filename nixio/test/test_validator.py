from __future__ import (absolute_import, division, print_function)
import nixio as nix
import numpy as np
import os
import unittest
from .tmp import TempDir

VE = nix.validator.ValidationError
VW = nix.validator.ValidationWarning


class TestValidate (unittest.TestCase):

    def setUp(self):
        # Create completely valid objects and break for each test
        self.tmpdir = TempDir("validatetest")
        self.testfilename = os.path.join(self.tmpdir.path, "validatetest.nix")
        self.file = nix.File.open(self.testfilename, nix.FileMode.Overwrite)
        for bidx in range(2):
            # Block
            blk = self.file.create_block("block-{}".format(bidx),
                                         "validation-test.block")
            for gidx in range(2):
                # Groups
                blk.create_group("group-{}".format(gidx),
                                 "validation-test.group")

            # DataArrays + Dimensions
            da1d = blk.create_data_array("data-1d",
                                         "validation-test.data_array",
                                         dtype=nix.DataType.Float,
                                         data=np.random.random(5))
            rdim = da1d.append_range_dimension(ticks=[0.1, 0.2, 1.5, 2.4, 3.0])
            rdim.unit = "ms"

            da2d = blk.create_data_array("data-2d",
                                         "validation-test.data_array",
                                         dtype=nix.DataType.Float,
                                         data=np.random.random((2, 10)))
            setdim = da2d.append_set_dimension()
            setdim.labels = ("A", "B")
            da2d.append_sampled_dimension(0.1)

            da3d = blk.create_data_array("data-3d",
                                         "validation-test.data_array",
                                         dtype=nix.DataType.Float,
                                         data=np.random.random((4, 2, 10)))
            setdim = da3d.append_set_dimension()
            setdim.labels = ("1", "2", "3", "4")
            da3d.append_set_dimension()  # set dim without labels
            smpldim = da3d.append_sampled_dimension(0.05)
            smpldim.unit = "s"

            # Tags + References + Features
            tag = blk.create_tag("tag", "validation-test.tag",
                                 position=(1, 1, 1))
            tag.extent = (2, 1, 5)
            tag.references.append(blk.data_arrays["data-3d"])
            tag.units = ("", "", "ms")

            pos1d = blk.create_data_array(
                "pos-1d", "validation-test.multi_tag.positions",
                data=[0, 1, 10, 20]
            )
            pos1d.append_set_dimension()

            tagwf = blk.create_tag("tag-wf", "validation-test.tag",
                                   position=(1, 3))
            tag_feat_data = blk.create_data_array(
                "feat-1", "validation-test.tag-feature", data=[1]
            )
            tag_feat_data.append_set_dimension()
            tagwf.create_feature(tag_feat_data, nix.LinkType.Untagged)

            # MultiTags + References + Features
            mtag1d = blk.create_multi_tag(
                "mtag1d", "validation-test.multi_tag", positions=pos1d
            )
            mtag1d.references.append(da1d)
            mtag1d.units = ("s",)

            pos2d = blk.create_data_array(
                "pos-2d", "validation-test.multi_tag.positions",
                data=[(10, 2, 100), (20, 5, 101)]
            )
            pos2d.append_set_dimension()
            pos2d.append_set_dimension()

            ext2d = blk.create_data_array(
                "ext-3d", "validation-test.multi_tag.extents",
                data=[(1, 1, 1), (5, 5, 5)]
            )
            ext2d.append_set_dimension()
            ext2d.append_set_dimension()
            mtag2d = blk.create_multi_tag(
                "mtag2d", "validation-test.multi_tag", positions=pos2d
            )
            mtag2d.extents = ext2d
            mtag2d.references.append(da3d)
            mtag2d.units = ("", "", "us")

            poswf = blk.create_data_array(
                "pos-wf", "validation-test.multi_tag.feature", data=[42]
            )
            poswf.append_set_dimension()
            mtagwf = blk.create_multi_tag(
                "mtag-wf", "validation-test.multi_tag.feature",
                positions=poswf
            )
            mtag_feat_data = blk.create_data_array(
                "feat-2", "validation-test.tag-feature", data=[4, 2]
            )
            mtag_feat_data.append_set_dimension()
            mtagwf.create_feature(mtag_feat_data, nix.LinkType.Untagged)

            # Sources
            # Go 3 levels deep (with N = 3:2:1)
            typestr = "validation-test.sources"
            for idx in range(3):
                isrc = blk.create_source("{}:{}".format(blk.name, idx),
                                         typestr)
                for jdx in range(2):
                    jsrc = isrc.create_source("{}:{}".format(isrc.name, jdx),
                                              typestr)
                    jsrc.create_source("{}:0".format(jsrc.name),
                                       typestr)

        # TODO: Add Sections and Properties

    def tearDown(self):
        self.file.close()
        self.tmpdir.cleanup()

    def test_all_valid(self):
        res = self.file.validate()
        assert not res["errors"], self.print_all_results(res)
        assert not res["warnings"], self.print_all_results(res)

    def test_check_file(self):
        self.file.version = tuple()
        res = self.file.validate()
        assert VW.NoVersion in res["warnings"][self.file]

        self.file.format = ""
        res = self.file.validate()
        assert VW.NoFormat in res["warnings"][self.file]

    def test_check_block(self):
        block = self.file.blocks[0]
        block._h5group.set_attr("name", None)
        res = self.file.validate()
        assert res["errors"][block] == [VE.NoName]

        block._h5group.set_attr("type", None)
        res = self.file.validate()
        actual = sorted(res["errors"][block])
        expected = sorted([VE.NoName, VE.NoType])
        assert actual == expected
        assert len(res["warnings"]) == 0

    def test_check_group(self):
        group1 = self.file.blocks[0].groups[0]
        group2 = self.file.blocks[1].groups[0]
        group1._h5group.set_attr("name", None)
        res = self.file.validate()
        assert res["errors"][group1] == [VE.NoName]
        assert group2 not in res["errors"]

        group2._h5group.set_attr("name", None)
        res = self.file.validate()
        assert res["errors"][group2] == [VE.NoName]

        assert group1 not in res["warnings"]
        assert group2 not in res["warnings"]

        group2._h5group.set_attr("type", None)
        res = self.file.validate()
        actual = sorted(res["errors"][group2])
        expected = sorted([VE.NoName, VE.NoType])
        assert actual == expected
        assert len(res["warnings"]) == 0

    def test_check_data_array_wrong_ticks(self):
        expmsg = VE.RangeDimTicksMismatch.format(1)
        da = self.file.blocks[0].data_arrays["data-1d"]
        rdim = da.dimensions[0]
        rdim.ticks = [10]
        res = self.file.validate()
        assert res["errors"][da] == [expmsg]

    def test_check_data_array_wrong_labels(self):
        expmsg = VE.SetDimLabelsMismatch.format(1)
        da = self.file.blocks[0].data_arrays["data-2d"]
        setdim = da.dimensions[0]
        setdim.labels = ["-"]
        res = self.file.validate()
        assert res["errors"][da] == [expmsg]

    def test_check_data_array_coefficients(self):
        da1 = self.file.blocks[0].data_arrays["data-1d"]
        da1.expansion_origin = 0.7

        da2 = self.file.blocks[1].data_arrays["data-1d"]
        da2.polynom_coefficients = [2, 4]

        res = self.file.validate()
        warnings = res["warnings"]
        assert warnings[da1] == [VW.NoPolynomialCoefficients]
        assert warnings[da2] == [VW.NoExpansionOrigin]

    def test_check_data_array_bad_dims(self):
        da = self.file.blocks[1].data_arrays["data-3d"]
        da.append_set_dimension()
        res = self.file.validate()
        assert res["errors"][da] == [VE.DimensionMismatch]

    def test_check_data_array_invalid_unit(self):
        da = self.file.blocks[1].data_arrays["data-1d"]
        da.unit = "whatevz"
        res = self.file.validate()
        assert res["warnings"][da] == [VW.InvalidUnit]

    def test_incorrect_dim_index(self):
        da = self.file.blocks[1].data_arrays["data-1d"]
        da.delete_dimensions()
        dimgroup = da._h5group.open_group("dimensions")
        # This wont work if we ever change the internals
        nix.SetDimension._create_new(dimgroup, "10")
        res = self.file.validate()
        assert VE.IncorrectDimensionIndex.format(1, 10) in res["errors"][da]

    def test_invalid_dim_index(self):
        da = self.file.blocks[1].data_arrays["data-1d"]
        da.delete_dimensions()
        dimgroup = da._h5group.open_group("dimensions")
        # This wont work if we ever change the internals
        nix.SetDimension._create_new(dimgroup, "-1")
        res = self.file.validate()
        assert VE.InvalidDimensionIndex.format(1) in res["errors"][da]

    def test_check_tag_no_pos(self):
        tag = self.file.blocks[0].tags[0]
        tag.position = []
        res = self.file.validate()
        tagerr = res["errors"][tag]
        # will also report mismatch in dimensions with reference
        assert "position is not set" in tagerr

    def test_check_tag_mismatch_dim(self):
        tag = self.file.blocks[0].tags[0]
        tag.position = [4, 3, 2, 1]
        res = self.file.validate()
        tagerr = res["errors"][tag]
        assert VE.PositionDimensionMismatch in tagerr

    def test_check_tag_invalid_unit(self):
        tag = self.file.blocks[0].tags[0]
        tag.units = ['abc']
        res = self.file.validate()
        tagerr = res["errors"][tag]
        assert VE.InvalidUnit in tagerr

    def test_check_tag_mismatch_units(self):
        tag = self.file.blocks[0].tags[0]
        tag.units = ("V", "A")
        res = self.file.validate()
        tagerr = res["errors"][tag]
        assert VE.ReferenceUnitsMismatch in tagerr

        tag.units = ("V", "A", "L")
        res = self.file.validate()
        tagerr = res["errors"][tag]
        assert VE.ReferenceUnitsIncompatible in tagerr

    def test_check_tag_pos_ext_mismatch(self):
        tag = self.file.blocks[0].tags[0]
        tag.extent = [100]

        res = self.file.validate()
        tagerr = res["errors"][tag]
        assert VE.ExtentDimensionMismatch in tagerr

    def test_check_multi_tag_no_pos(self):
        blk = self.file.blocks[0]
        mtag = blk.multi_tags["mtag1d"]
        mtag.positions = blk.create_data_array("empty", "bork", data=[])
        res = self.file.validate()
        mtagerr = res["errors"][mtag]
        # will also report mismatch in dimensions with reference
        assert VE.NoPositions in mtagerr

    def test_check_multi_tag_mismatch_dim(self):
        blk = self.file.blocks[0]
        mtag = blk.multi_tags["mtag2d"]
        mtag.positions = blk.create_data_array("wrong dim", "bork",
                                               data=[(1, 1), (2, 2)])
        res = self.file.validate()
        mtagerr = res["errors"][mtag]
        assert VE.PositionsDimensionMismatch in mtagerr

    def test_check_multi_tag_invalid_unit(self):
        blk = self.file.blocks[0]
        mtag = blk.multi_tags["mtag2d"]
        mtag.units = ['abc']
        res = self.file.validate()
        tagerr = res["errors"][mtag]
        assert VE.InvalidUnit in tagerr

    def test_check_multi_tag_mismatch_units(self):
        mtag = self.file.blocks[0].multi_tags["mtag2d"]
        mtag.units = ("V", "A")
        res = self.file.validate()
        tagerr = res["errors"][mtag]
        assert VE.ReferenceUnitsMismatch in tagerr

        mtag.units = ("V", "A", "L")
        res = self.file.validate()
        tagerr = res["errors"][mtag]
        assert VE.ReferenceUnitsIncompatible in tagerr

    def test_check_multi_tag_pos_ext_mismatch(self):
        blk = self.file.blocks[0]
        mtag = blk.multi_tags["mtag2d"]
        mtag.extents = blk.create_data_array("wrong dim", "bork",
                                             data=[(1, 1), (2, 2)])

        res = self.file.validate()
        mtagerr = res["errors"][mtag]
        assert VE.PositionsExtentsMismatch in mtagerr

    def test_check_source(self):
        # just break one of the deepest sources
        def get_deepest_source(sources):
            for source in sources:
                if not source.sources:
                    return source
                return get_deepest_source(source.sources)

        source = get_deepest_source(self.file.blocks[0].sources)
        source._h5group.set_attr("name", None)
        source._h5group.set_attr("type", None)

        res = self.file.validate()
        assert len(res["errors"][source]) == 2
        assert len(res["warnings"]) == 0
        assert sorted(res["errors"][source]) == sorted([VE.NoName, VE.NoType])

    def _test_check_section(self):  # only have check for basics now
        sec1 = self.file.sections[0]
        sec1._h5group.set_attr("type", None)
        self.validator.check_section(sec1, 0)
        err = self.validator.errors['sections'][0]['errors']
        assert "Type of Section is missing" in err

    def _test_check_props(self):
        # check1
        section = self.file.sections[0]
        prop = section.create_property("prop1", [1, 2, 3, 4])
        self.validator.form_dict()
        # check2
        prop1 = section.create_property("prop2", values_or_dtype=[1, 2, 3, 4])
        prop1.delete_values()
        prop1._h5group.set_attr('name', None)
        # check3
        prop2 = section.create_property("prop3", values_or_dtype=[1, 2, 3, 4])
        prop2.unit = "invalidu"
        self.validator.form_dict()
        self.validator.check_property(prop, 0, 0)  # check1
        err = self.validator.errors['sections'][0]['props'][0]['errors']
        assert "Unit is not set" in err
        # check2 - nameerr but no uniterr
        self.validator.check_property(prop1, 1, 0)
        err = self.validator.errors['sections'][0]['props'][1]['errors']
        assert err == ['Name is not set!']
        self.validator.check_property(prop2, 2, 0)  # check3
        err = self.validator.errors['sections'][0]['props'][2]['errors']
        assert 'Unit is not valid!' in err

    def _test_range_dim(self):
        err_dict = self.validator.errors['blocks'][0]['data_arrays']
        # check1
        da1 = self.block1.data_arrays[0]
        rdim1 = da1.append_range_dimension([0.55, 0.10, 0.1])
        # for dims and prop test we need to form_dict again
        self.validator.form_dict()
        rdim1._h5group.set_attr('dimension_type', 'set')
        # check2
        rdim2 = da1.append_range_dimension([])
        rdim2._h5group.set_attr("unit", "m/s")  # compound unit

        self.validator.form_dict()
        self.validator.check_range_dim(rdim1, 0, 0, 0)  # check1
        err = err_dict[0]['dimensions'][0]['errors']
        assert "Dimension type is not correct!" in err
        assert "Ticks are not sorted!" in err
        self.validator.check_range_dim(rdim2, 1, 0, 0)  # check2
        err = err_dict[0]['dimensions'][1]['errors']
        assert "Ticks need to be set for range dimensions" in err
        assert "Unit must be atomic, not composite!" in err

    def _test_sample_dim(self):
        # check1
        da1 = self.block1.data_arrays[0]
        sdim1 = da1.append_sampled_dimension(sampling_interval=0.5)
        sdim1._h5group.set_attr('dimension_type', 'set')
        sdim1.offset = 0.1

        # check2
        sdim2 = da1.append_sampled_dimension(sampling_interval=-0.5)
        sdim2.unit = "m/s"

        self.validator.form_dict()
        self.validator.check_sampled_dim(sdim1, 0, 0, 0)  # check1
        da = self.validator.errors['blocks'][0]['data_arrays'][0]
        err = da['dimensions'][0]['errors']
        assert "Dimension type is not correct!" in err
        assert "Offset is set, but no unit set!" in err
        self.validator.check_sampled_dim(sdim2, 1, 0, 0)  # check2
        err = da['dimensions'][1]['errors']
        assert "Unit must be atomic, not composite!" in err
        assert "SamplingInterval is not set to valid value (> 0)!" in err

    def _test_set_dim(self):
        da1 = self.block1.data_arrays[0]
        setdim1 = da1.append_set_dimension()
        setdim1._h5group.set_attr('dimension_type', 'range')
        self.validator.form_dict()
        self.validator.check_set_dim(setdim1, 0, 0, 0)
        da = self.validator.errors['blocks'][0]['data_arrays'][0]
        dimerr = da['dimensions'][0]['errors']
        assert "Dimension type is not correct!" in dimerr

    def _test_sources(self):
        da1 = self.block1.data_arrays[0]
        src1 = self.block1.create_source("src1", "testing_src")
        da1.sources.append(src1)
        src1._h5group.set_attr('name', None)
        self.validator.form_dict()
        self.validator.check_sources(src1, 0)
        err = self.validator.errors['blocks'][0]['sources']
        assert "Name of Source is missing" in err

    @staticmethod
    def print_all_results(res):
        print("Errors")
        for obj, msg in res["errors"].items():
            name = obj.name if hasattr(obj, "name") else str(obj)
            print("  {}: {}".format(name, msg))
        print("Warnings")
        for obj, msg in res["warnings"].items():
            name = obj.name if hasattr(obj, "name") else str(obj)
            print("  {}: {}".format(name, msg))
