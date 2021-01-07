# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2018,2020 Canonical Ltd
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

import collections
import contextlib
import logging
from typing import Any, Dict, List, Optional, Set

from partbuilder import errors
from partbuilder._part import Part, get_dependencies
from partbuilder._step import (
    STEPS,
    Step,
    dependency_prerequisite_step,
)
from ._dirty_report import DirtyReport
from ._outdated_report import OutdatedReport
from ..states import load_state, PartState

# report types
_DirtyReport = Dict[str, Dict[Step, Optional[DirtyReport]]]
_OutdatedReport = Dict[str, Dict[Step, Optional[OutdatedReport]]]

logger = logging.getLogger(__name__)


class Dependency:
    def __init__(self, *, part_name, step):
        self.part_name = part_name
        self.step = step


class _EphemeralStates:
    """A pure memory-backed state control

    An ephemeral state initialized from the persistent state for all
    parts. We use the memory-backed global state when computing the list
    of step actions to execute.
    """

    def __init__(self, parts: List[Part]):
        self._state = {}

        for p in parts:
            self._state[p.name] = {}  # type: Dict[str, Dict[Step, PartState]]

            # Initialize from persistent state
            for s in STEPS:
                state = load_state(p, s)
                if state.timestamp:
                    self.add(part_name=p.name, step=s, state=state)

    def add(self, *, part_name: str, step: Step, state: PartState) -> None:
        self._state[part_name][step] = state

    def remove(self, *, part_name: str, step: Step) -> None:
        self._state[part_name].pop(step)

    def test(self, *, part_name: str, step: Step) -> bool:
        return step in self._state[part_name]

    def state(self, *, part_name: str, step: Step) -> Optional[PartState]:
        if self.test(part_name=part_name, step=step):
            return self._state[part_name][step]
        return None

    def dirty_report_for_part(self, *, part_name: str, step: Step) -> Optional[_DirtyReport]:
        """Return a DirtyReport class describing why the step is dirty.

        A step is considered to be dirty if either YAML properties used by it
        (`stage-packages` are used by the `pull` step, for example), or project
        options used by it (`--target-arch` is used by the `pull` step as well)
        have changed since the step was run. This means the step needs to be
        cleaned and run again. This is in contrast to an "outdated" step, which
        typically doesn't need to be cleaned, just updated with files from an
        earlier step in the lifecycle.

        :param steps.Step step: The step to be checked.
        :returns: DirtyReport if the step is dirty, None otherwise.
        """

        # Retrieve the stored state for this step (assuming it has already run)
        s = self.state(part_name=part_name, step=step)
        if s:
            # state properties contains the old state that this step cares
            # about, and we're comparing it to those same keys in the current
            # state (current_properties). If they've changed, then this step
            # is dirty and needs to run again.
            #properties = state.diff_properties_of_interest(current_properties)
            properties = None

            # state project_options contains the old project options that this
            # step cares about, and we're comparing it to those same options in
            # the current state. If they've changed, then this step is dirty
            # and needs to run again.
            #options = state.diff_project_options_of_interest(current_project_options)
            options = None

            if properties or options:
                return DirtyReport(
                    dirty_properties=properties, dirty_project_options=options
                )
 
        return None

    def outdated_report_for_part(self, *, part_name: str, step: Step) -> Optional[_OutdatedReport]:
        """Return an OutdatedReport class describing why the step is outdated.

        A step is considered to be outdated if an earlier step in the lifecycle
        has been run more recently, or if the source code changed on disk.
        This means the step needs to be updated by taking modified files from
        the previous step. This is in contrast to a "dirty" step, which must
        be cleaned and run again.

        :param steps.Step step: The step to be checked.
        :returns: OutdatedReport if the step is outdated, None otherwise.
        """

        # FIXME:SPIKE: implement outdated check

        return None


class StateManager:
    """The StatusCache is a lazy caching interface for the status of parts."""

    def __init__(self, parts: List[Part]) -> None:
        """Create a new StatusCache.

        :param _config.Config config: Project config.
        """
        self._parts = parts
        self._eph_states = _EphemeralStates(parts)
        self._steps_run: Dict[str, Set[Step]] = dict()
        self._outdated_reports: _OutdatedReport = collections.defaultdict(dict)
        self._dirty_reports: _DirtyReport = collections.defaultdict(dict)

    def state(self, part: Part, step: Step) -> Optional[PartState]:
        return self._eph_states.state(part_name=part.name, step=step)

    def set_state(self, part: Part, step: Step, *, state: PartState) -> None:
        self._eph_states.add(part_name=part.name, step=step, state=state)

    def should_step_run(self, part: Part, step: Step) -> bool:
        """Determine if a given step of a given part should run.

        :param Part part: Part in question.
        :param Step step: Step in question.
        :return: Whether or not step should run.
        :rtype: bool

        A given step should run if it:
            1. Hasn't yet run
            2. Is dirty
            3. Is outdated
            4. Either (1), (2), or (3) apply to any earlier steps in the part's
               lifecycle
        """
        if (
            not self.has_step_run(part, step)
            or self.outdated_report(part, step) is not None
            or self.dirty_report(part, step) is not None
        ):
            return True

        previous_steps = step.previous_steps()
        if previous_steps:
            return self.should_step_run(part, previous_steps[-1])

        return False

    def add_step_run(self, part: Part, step: Step) -> None:
        """Cache the fact that a given step has now run for the given part.

        :param Part part: Part in question.
        :param Step step: Step in question.
        """
        self._ensure_steps_run(part)
        self._steps_run[part.name].add(step)

    def has_step_run(self, part: Part, step: Step) -> bool:
        """Determine if a given step of a given part has already run.

        :param Part part: Part in question.
        :param Step step: Step in question.
        :return: Whether or not the step has run.
        :rtype: bool
        """
        self._ensure_steps_run(part)
        return step in self._steps_run[part.name]

    def outdated_report(self, part: Part, step: Step):
        """Obtain the outdated report for a given step of the given part.

        :param Part part: Part in question.
        :param Step step: Step in question.
        :return: Outdated report (could be None)
        :rtype: OutdatedReport
        """
        self._ensure_outdated_report(part, step)
        return self._outdated_reports[part.name][step]

    def dirty_report(self, part: Part, step: Step) -> Optional[DirtyReport]:
        """Obtain the dirty report for a given step of the given part.

        :param Part part: Part in question.
        :param Step step: Step in question.
        :return: Dirty report (could be None)
        :rtype: DirtyReport
        """
        self._ensure_dirty_report(part, step)
        return self._dirty_reports[part.name][step]

    def clear_step(self, part: Part, step: Step) -> None:
        """Clear the given step of the given part from the cache.

        :param Part part: Part in question.
        :param Step step: Step in question.

        This function does nothing if the step wasn't cached.
        """
        if part.name in self._steps_run:
            _remove_item_from_set(self._steps_run[part.name], step)
            if not self._steps_run[part.name]:
                _remove_key_from_dict(self._steps_run, part.name)
        _remove_key_from_dict(self._outdated_reports[part.name], step)
        if not self._outdated_reports[part.name]:
            _remove_key_from_dict(self._outdated_reports, part.name)
        _remove_key_from_dict(self._dirty_reports[part.name], step)
        if not self._dirty_reports[part.name]:
            _remove_key_from_dict(self._dirty_reports, part.name)

    def _ensure_steps_run(self, part: Part) -> None:
        if part.name not in self._steps_run:
            self._steps_run[part.name] = self._get_steps_run(part)

    def _ensure_outdated_report(self, part: Part, step: Step) -> None:
        if step not in self._outdated_reports[part.name]:
            # self._outdated_reports[part.name][step] = part.get_outdated_report(step)
            self._outdated_reports[part.name][step] = self._eph_states.outdated_report_for_part(part_name=part.name, step=step)

    def _ensure_dirty_report(self, part: Part, step: Step) -> None:
        # If we already have a dirty report, bail
        if step in self._dirty_reports[part.name]:
            return

        # Get the dirty report from the PluginHandler. If it's dirty, we can
        # stop here
        dr = self._eph_states.dirty_report_for_part(part_name=part.name, step=step)
        self._dirty_reports[part.name][step] = dr
        if dr:
            return

        # The dirty report from the PluginHandler only takes into account
        # properties specific to that part. If it's not dirty because of those,
        # we need to expand it here to also take its dependencies (if any) into
        # account
        prerequisite_step = dependency_prerequisite_step(step)
        dependencies = get_dependencies(part.name, parts=self._parts, recursive=True)

        changed_dependencies: List[Dependency] = []

        # with contextlib.suppress(errors.StepHasNotRun):

        # timestamp = part.step_timestamp(step)
        this_state = self._eph_states.state(part_name=part.name, step=step)

        for dependency in dependencies:
            # Make sure the prerequisite step of this dependency has not
            # run more recently than (or should run _before_) this step.
            # try:
                # prerequisite_timestamp = dependency.step_timestamp(prerequisite_step)

            prerequisite_state = self._eph_states.state(part_name=dependency.name, step=prerequisite_step)
            if prerequisite_state and this_state:
                prerequisite_timestamp = prerequisite_state.timestamp
                dependency_changed = this_state.timestamp < prerequisite_timestamp
            else: 
                dependency_changed = False

            # except errors.StepHasNotRunError:
            #     dependency_changed = True
            # else:
            #     dependency_changed = timestamp < prerequisite_timestamp

            if dependency_changed or self.should_step_run(
                dependency, prerequisite_step
            ):
                changed_dependencies.append(
                    Dependency(part_name=dependency.name, step=prerequisite_step)
                )

        if changed_dependencies:
            self._dirty_reports[part.name][step] = DirtyReport(
                changed_dependencies=changed_dependencies
            )

    def _get_steps_run(self, part: Part) -> Set[Step]:
        steps_run = set()  # type: Set[Step]
        for step in STEPS:
            if not self._should_step_run_for_part(step=step, part=part):
                steps_run.add(step)

        return steps_run

    def _should_step_run_for_part(self, *, part: Part, step: Step) -> bool:
        """Return true if the given step hasn't run (or has been cleaned)."""

        latest_step = self._latest_step_for_part(part)
        if not latest_step:
            return True
        return step > latest_step

    def _latest_step_for_part(self, part: Part) -> Optional[Step]:
        for step in reversed(STEPS):
            if self._eph_states.test(part_name=part.name, step=step):
                return step
        return None

    def is_state_clean_for_part(self, *, part: Part, step: Step) -> bool:
        """Return true if the given step hasn't run (or has been cleaned)."""

        latest_step = self._latest_step_for_part(part=part)
        if not latest_step:
            return True
        return step > latest_step

    def clean_part(self, part: Part, step: Step) -> None:
        for s in reversed(STEPS):
            if step <= s:
                if not self.is_state_clean_for_part(part=part, step=s):
                    self._mark_step_clean_for_part(part=part, step=s)

    def _mark_step_clean_for_part(self, part: Part, step: Step):
        # remove state from ephemeral cache
        self._eph_states.remove(part_name=part.name, step=step)


def _remove_key_from_dict(c: Dict[Any, Any], key: Any) -> None:
    with contextlib.suppress(KeyError):
        del c[key]


def _remove_item_from_set(c: Set[Any], key: Any) -> None:
    with contextlib.suppress(KeyError):
        c.remove(key)
