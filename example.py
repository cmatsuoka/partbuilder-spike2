#!/usr/bin/env python3

import logging
import partbuilder
import sys
import yaml
from partbuilder import Action, Step

def msg(a: partbuilder.PartAction):
    action_message = {
        Action.PULL: "Pulling",
        Action.BUILD: "Building",
        Action.STAGE: "Staging",
        Action.PRIME: "Priming",
        Action.REPULL: "Repulling",
        Action.REBUILD: "Rebuildng",
        Action.RESTAGE: "Restaging",
        Action.REPRIME: "Repriming",
    }

    if a.reason:
        return f"{action_message[a.action]} {a.part_name} (because {a.reason})"
    else:
        return f"{action_message[a.action]} {a.part_name}"


def parse_step(s: str) -> Step:
    step_map = {
        "pull": Step.PULL,
        "build": Step.BUILD,
        "stage": Step.STAGE,
        "prime": Step.PRIME,
    }

    return step_map.get(s, Step.PRIME)


def main():
    logging.basicConfig(level=logging.DEBUG)

    with open("parts.yaml") as f:
        parts = yaml.safe_load(f)

    target_step = parse_step(sys.argv[1]) if len(sys.argv) > 1 else Step.PRIME
    part_names = sys.argv[2:] if len(sys.argv) > 2 else []

    lf = partbuilder.LifecycleManager(parts=parts)
    actions = lf.actions(target_step, part_names)

    for a in actions:
        print(msg(a))

    lf.execute(actions)


if __name__ == "__main__":
    main()
