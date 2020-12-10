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

from typing import Any, Callable, Dict, List

from ._stepinfo import StepInfo
from ._part import Part
from ._step import Step
from partbuilder import sequencer
from partbuilder.plugins import Plugin


class LifecycleManager:
    def __init__(
        self,
        *,
        parts: Dict[str, Any],
        build_packages: List[str] = [],
        work_dir: str = ".",
        target_arch: str = "",
        platform_id: str = "",
        platform_version_id: str = "",
        parallel_build_count: int = 1,
        local_plugins_dir: str = "",
        **custom_args,  # custom passthrough args
    ):
        # self._validator = Validator(parts)
        # self._validator.validate()

        parts_data = parts.get("parts", {})
        self._parts = [
            Part(name, p, work_dir=work_dir) for name, p in parts_data.items()
        ]
        self._build_packages = build_packages
        self._sequencer = sequencer.Sequencer(self._parts)

        self._step_info = StepInfo(
            work_dir=work_dir,
            target_arch=target_arch,
            platform_id=platform_id,
            platform_version_id=platform_version_id,
            parallel_build_count=parallel_build_count,
            local_plugins_dir=local_plugins_dir,
        )

    def clean(self, parts: List[str] = []) -> None:
        pass

    def actions(self, step: Step, parts: List[str] = []) -> None:
        act = self._sequencer.actions(step, parts)
        return act


def register_pre_step_callback(
    callback: Callable[[StepInfo], None], steps: List[str]
) -> None:
    pass


def register_post_step_callback(
    callback: Callable[[StepInfo], None], steps: List[str]
) -> None:
    pass


def register_plugin(plugins: Dict[str, Plugin]) -> None:
    pass
