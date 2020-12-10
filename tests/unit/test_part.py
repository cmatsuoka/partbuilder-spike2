# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015-2019 Canonical Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from testtools.matchers import Equals

from tests import unit
from partbuilder import _part
from partbuilder import errors
from partbuilder._part import Part


class TestPartOrdering(unit.TestCase):
    def test_sort_parts(self):
        p1 = Part("foo", {})
        p2 = Part("bar", {"after": ["baz"]})
        p3 = Part("baz", {"after": ["foo"]})

        x = _part.sort_parts([p1, p2, p3])
        self.assertThat(x, Equals([p1, p3, p2]))

    def test_sort_parts_cycle(self):
        p1 = Part("foo", {})
        p2 = Part("bar", {"after": ["baz"]})
        p3 = Part("baz", {"after": ["bar"]})

        raised = self.assertRaises(
            errors.PartbuilderPartDependencyCycle, _part.sort_parts, [p1, p2, p3]
        )
        self.assertThat(raised._part_name, Equals("bar"))


class TestPartDependencies(unit.TestCase):
    def test_get_dependencies(self):
        p1 = Part("foo", {})
        p2 = Part("bar", {"after": ["baz"]})
        p3 = Part("baz", {"after": ["foo"]})

        x = _part.get_dependencies("foo", parts=[p1, p2, p3])
        self.assertThat(x, Equals(set()))

        x = _part.get_dependencies("bar", parts=[p1, p2, p3])
        self.assertThat(x, Equals({p3}))

        x = _part.get_dependencies("bar", parts=[p1, p2, p3], recursive=True)
        self.assertThat(x, Equals({p3, p1}))

        raised = self.assertRaises(
            errors.PartbuilderInvalidPartName,
            _part.get_dependencies,
            "invalid",
            parts=[p1, p2, p3],
        )
        self.assertThat(raised._part_name, Equals("invalid"))
