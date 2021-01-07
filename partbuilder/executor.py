
import logging
import os.path
from pathlib import Path

from ._part import Part
from ._step import Action
from ._stepinfo import StepInfo

logger = logging.getLogger(__name__)


def run_action(action: Action, *, part: Part, step_info: StepInfo):
    logger.debug(f"execute action {part.name}:{action!r}")

    # TODO: load plugin for part, instantiate part handler, etc.

    if action == Action.PULL:
        _run_pull(part, step_info)

    if action == Action.BUILD:
        _run_build(part, step_info)

    if action == Action.STAGE:
        _run_stage(part, step_info)

    if action == Action.PRIME:
        _run_prime(part, step_info)



def _run_pull(part: Part, step_info: StepInfo):
    _save_state_file(part, "pull")
        

def _run_build(part: Part, step_info: StepInfo):
    _save_state_file(part, "build")
        

def _run_stage(part: Part, step_info: StepInfo):
    _save_state_file(part, "stage")
        

def _run_prime(part: Part, step_info: StepInfo):
    _save_state_file(part, "prime")
        

def _save_state_file(part: Part, name: str) -> None:
    if not os.path.exists(part.part_state_dir):
        os.makedirs(part.part_state_dir)

    state_file = os.path.join(part.part_state_dir, name)
    Path(state_file).touch()
