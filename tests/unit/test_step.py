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
from partbuilder import _step
from partbuilder._step import Step, Action


class TestStep(unit.TestCase):
    def test_previous_steps(self):
        for s, p in {
            Step.PULL: [],
            Step.BUILD: [Step.PULL],
            Step.STAGE: [Step.PULL, Step.BUILD],
            Step.PRIME: [Step.PULL, Step.BUILD, Step.STAGE],
        }.items():
            prev = s.previous_steps()
            self.assertThat(prev, Equals(p))

    def test_step_to_action(self):
        for s, a in {
            Step.PULL: Action.PULL,
            Step.BUILD: Action.BUILD,
            Step.STAGE: Action.STAGE,
            Step.PRIME: Action.PRIME,
        }.items():
            act = s.to_action()
            self.assertThat(act, Equals(a))


class TestStepHelpers(unit.TestCase):
    def test_dependency_prerequisite_step(self):
        for s, p in {
            Step.PULL: Step.STAGE,
            Step.BUILD: Step.STAGE,
            Step.STAGE: Step.STAGE,
            Step.PRIME: Step.PRIME,
        }.items():
            preq = _step.dependency_prerequisite_step(s)
            self.assertThat(preq, Equals(p))
