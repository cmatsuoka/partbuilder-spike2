# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2020 Canonical Ltd
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

import enum
from typing import List, TYPE_CHECKING

from partbuilder import errors


if TYPE_CHECKING:
    from partbuilder.sequencer.states import PartState


@enum.unique
class Action(enum.IntEnum):
    CLEAN = 0
    PULL = 1
    BUILD = 2
    STAGE = 3
    PRIME = 4
    SKIP = 5
    REMOVE = 6
    INSTALL_PKG = 7
    INSTALL_STAGE_PKG = 8
    UPDATE_PULL = 9
    UPDATE_BUILD = 10

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"


@enum.unique
class Step(enum.IntEnum):
    PULL = 1
    BUILD = 2
    STAGE = 3
    PRIME = 4

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"

    def previous_steps(self) -> List["Step"]:
        steps = []

        if self >= Step.BUILD:
            steps.append(Step.PULL)
        if self >= Step.STAGE:
            steps.append(Step.BUILD)
        if self >= Step.PRIME:
            steps.append(Step.STAGE)

        return steps

    def next_steps(self) -> List["Step"]:
        steps = []

        if self == Step.PULL:
            steps.append(Step.BUILD)
        if self <= Step.BUILD:
            steps.append(Step.STAGE)
        if self <= Step.STAGE:
            steps.append(Step.PRIME)

        return steps

    def to_action(self) -> Action:
        if self == Step.PULL:
            return Action.PULL
        if self == Step.BUILD:
            return Action.BUILD
        if self == Step.STAGE:
            return Action.STAGE
        if self == Step.PRIME:
            return Action.PRIME

        raise errors.PartbuilderInternalError(f"Invalid step {self!s}")


STEPS = [
    Step.PULL,
    Step.BUILD,
    Step.STAGE,
    Step.PRIME,
]


class PartAction:
    def __init__(self, part_name: str, action: Action):
        self.part_name = part_name
        self.action = action

    def __repr__(self):
        return f"{self.part_name}:{self.action!r}"

    def state(self) -> "PartState":
        return self._state

    def set_state(self, value: "PartState") -> "PartAction":
        self._state = value
        return self


class StepActions:
    def __init__(self, part_name: str, step: Step, *, comment: str = ""):
        self.part_name = part_name
        self.step = step
        self.actions = []  # type: List[PartAction]
        self.comment = comment

    def add(self, pact: PartAction) -> None:
        self.actions.append(pact)

    def __repr__(self):
        if self.comment:
            return f"{self.part_name}:{self.step!r}: {self.actions} ({self.comment})"
        else:
            return f"{self.part_name}:{self.step!r}: {self.actions}"


def dependency_prerequisite_step(step: Step) -> Step:
    if step <= Step.STAGE:
        return Step.STAGE
    else:
        return step
