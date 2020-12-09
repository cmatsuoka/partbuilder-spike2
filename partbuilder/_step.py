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


@enum.unique
class Step(enum.Enum):
    CLEAR = 0
    PULL = 1
    BUILD = 2
    STAGE = 3
    PRIME = 4

   def __str__(self):
       return self.name.lower()

   def previous_steps(self): -> List[Step]:
       pass


class StepAction:
    def __init__(self, part_name: str, step: Step, *, comment: str=""):
        self.name = name
        self.step = step
        self.comment = comment

    def __repr__(self):
        if comment:
            return f"{self.name}: {self.step!s} ({self.comment})"
        else:
            return f"{self.name}: {self.step!s}"
