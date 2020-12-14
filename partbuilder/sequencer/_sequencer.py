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

import logging
from typing import List

from .state_manager import StateManager, DirtyReport, OutdatedReport
from partbuilder._step import Action, PartAction, Step, StepActions
from partbuilder._part import Part, sort_parts

logger = logging.getLogger(__name__)


class Sequencer:
    def __init__(self, parts: List[Part]):
        self._parts = sort_parts(parts)
        self._sm = StateManager(parts)
        self._actions = []  # type: List[PartAction]

    def actions(
        self, target_step: Step, part_names: List[str] = []
    ) -> List[StepActions]:
        """Determine the list of steps to execute for each part."""

        if part_names:
            selected_parts = [p for p in self._parts if p.name in part_names]
        else:
            selected_parts = self._parts

        self._actions = []
        for current_step in target_step.previous_steps() + [target_step]:
            for p in selected_parts:
                logger.debug(f"process {p.name}:Step.{current_step.name}")
                self._add_step_actions(current_step, target_step, p, part_names)

        return self._actions

    def _add_step_actions(
        self, current_step: Step, target_step: Step, part: Part, part_names: List[str]
    ) -> None:
        """Verify if this step should be executed."""

        # check if step already ran, if not then run it
        if not self._sm.has_step_run(part, current_step):
            actions = StepActions(part.name, current_step)
            actions.add(PartAction(part.name, current_step.to_action()))
            self._actions.append(actions)
            return

        # If the step has already run:
        #
        # 1. If the step is the exact step that was requested, and the part was
        #    explicitly listed, run it again.

        if part_names and current_step == target_step and part.name in part_names:
            actions = StepActions(part.name, current_step, comment="requested step")
            actions.add(PartAction(part.name, current_step.to_action()))
            self._actions.append(actions)
            return

        # 2. If the step is dirty, run it again. A step is considered dirty if
        #    properties used by the step have changed, project options have changed,
        #    or dependencies have been re-staged.

        dirty_report = self._sm.dirty_report(part, current_step)
        if dirty_report:
            self._handle_dirty(part, current_step, dirty_report)
            return

        # 3. If the step is outdated, run it again (without cleaning if possible).
        #    A step is considered outdated if an earlier step in the lifecycle
        #    has been re-executed.

        outdated_report = self._sm.outdated_report(part, current_step)
        if outdated_report:
            self._handle_outdated(part, current_step, dirty_report)
            return

        # 4. Otherwise just skip it

        actions = StepActions(part.name, current_step, comment="already ran")
        actions.add(PartAction(part.name, Action.SKIP))
        self._actions.append(actions)

    def _handle_dirty(self, part: Part, step: Step, dirty_report: DirtyReport,) -> None:
        actions = StepActions(part.name, step, comment="dirty")

        # First clean the step, then run it again
        self.sm._clean_part(part, step, actions=actions)

        # Uncache this and later steps since we just cleaned them: their status
        # has changed
        # FIXME: remove from ephemeral cache
        for current_step in [step] + step.next_steps():
            self._sm.clear_step(part, current_step)

        actions.add(PartAction(part.name, current_step.to_action()))

    def _handle_outdated(
        self, part: Part, step: Step, outdated_report: OutdatedReport
    ) -> None:
        actions = StepActions(part.name, step, comment="outdated")
        actions.add(PartAction(part.name, step.to_action()))
        self._actions.append(actions)
