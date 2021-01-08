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
from typing import List, Optional

from .state_manager import StateManager, DirtyReport, OutdatedReport
from .states import PartState
from partbuilder._step import Action, dependency_prerequisite_step, PartAction, Step, action_for_step, rerun_action_for_step, skip_action_for_step
from partbuilder._part import get_dependencies, Part, sort_parts

logger = logging.getLogger(__name__)


class Sequencer:
    def __init__(self, parts: List[Part]):
        self._parts = sort_parts(parts)
        self._sm = StateManager(parts)
        self._actions = []  # type: List[PartAction]

    def actions(
        self, target_step: Step, part_names: List[str] = []
    ) -> List[PartAction]:
        """Determine the list of steps to execute for each part."""

        self._actions = []
        self._add_all_actions(target_step, part_names)
        return self._actions


    def _add_all_actions(self, target_step: Step, part_names: List[str] = []) -> None:
        if part_names:
            selected_parts = [p for p in self._parts if p.name in part_names]
        else:
            selected_parts = self._parts

        for current_step in target_step.previous_steps() + [target_step]:
            # TODO: if step is STAGE, check for collisions

            for p in selected_parts:
                logger.debug(f"process {p.name}:Step.{current_step.name}")
                self._add_step_actions(current_step, target_step, p, part_names)


    def _add_step_actions(
        self, current_step: Step, target_step: Step, part: Part, part_names: List[str]
    ) -> None:
        """Verify if this step should be executed."""

        # check if step already ran, if not then run it
        if not self._sm.has_step_run(part, current_step):
            self._run_step(part, current_step)
            return

        # If the step has already run:
        #
        # 1. If the step is the exact step that was requested, and the part was
        #    explicitly listed, run it again.

        if part_names and current_step == target_step and part.name in part_names:
            self._rerun_step(part, current_step, reason="requested step")
            return

        # 2. If the step is dirty, run it again. A step is considered dirty if
        #    properties used by the step have changed, project options have changed,
        #    or dependencies have been re-staged.

        dirty_report = self._sm.dirty_report(part, current_step)
        if dirty_report:
            logger.debug(f"{part.name}:{current_step!r} is dirty: {dirty_report.summary()}")
            self._rerun_step(part, current_step, reason=dirty_report.summary())
            return

        # 3. If the step is outdated, run it again (without cleaning if possible).
        #    A step is considered outdated if an earlier step in the lifecycle
        #    has been re-executed.

        outdated_report = self._sm.outdated_report(part, current_step)
        if outdated_report:
            logger.debug(f"{part.name}:{current_step!r} is outdated")
            if step == PULL or step == BUILD:
                self._update_step(part, step, reason=outdated_report.summary())
            else:
                self._rerun_step(part, step, reason=outdated_report.summary())

            return

        # 4. Otherwise just skip it
        self._add_action(part, skip_action_for_step(current_step), reason="already ran")


    def _prepare_step(self, part: Part, step: Step) -> None:
        all_deps = get_dependencies(part.name, parts=self._parts)
        if step > Step.PULL:  # With v2 plugins we don't need to stage dependencies before PULL
            prerequisite_step = dependency_prerequisite_step(step)
            deps = { p for p in all_deps if self._sm.should_step_run(p, prerequisite_step) }

            for d in deps:
                self._add_all_actions(target_step=prerequisite_step, part_names=[d.name])


    def _run_step(self, part: Part, step: Step, *, reason: Optional[str]=None, rerun: bool=False) -> None:
        self._prepare_step(part, step)

        state = None

        if step is Step.PULL:
            pull_properties = dict()
            part_build_packages = []  # self._grammar_processor.get_build_packages()
            part_build_snaps = []     #self._grammar_processor.get_build_snaps()

            # TODO: build pull state

            self._sm.set_state(part=part, step=step, state=state)

        if step is Step.BUILD:
            # TODO: build and update ephemeral build state
            pass

        if rerun:
            self._add_action(part, rerun_action_for_step(step), reason=reason, state=state)
        else:
            self._add_action(part, action_for_step(step), reason=reason, state=state)

        self._sm.add_step_run(part, step)


    def _rerun_step(self, part: Part, step: Step, *, reason: Optional[str]=None) -> None:
        logger.debug(f"rerun step {part.name}:{step!r}")
        # First clean the step, then run it again
        self._sm.clean_part(part, step)

        # Uncache this and later steps since we just cleaned them: their status
        # has changed
        # FIXME: remove from ephemeral cache
        for current_step in [step] + step.next_steps():
            self._sm.clear_step(part, current_step)

        self._run_step(part, step, reason=reason, rerun=True)

    def _update_step(self, part: Part, step: Step):
        pass



    def _add_action(self, part: Part, action: Action, *, reason: Optional[str]=None, state: Optional[PartState]=None) -> None:
        logger.debug(f"add action {part.name}:{action!r}")
        self._actions.append(PartAction(part.name, action, reason=reason, state=state))
