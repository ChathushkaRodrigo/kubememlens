"""Retain allow-listed readiness counts when an owned kind fixture cannot start."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from common import ContractError, MAX_BYTES, privacy, require, write_new

PHASES = {"Pending", "Running", "Succeeded", "Failed", "Unknown"}
REASONS = {"ContainerCreating", "PodInitializing", "ErrImagePull", "ImagePullBackOff",
           "ErrImageNeverPull", "CreateContainerConfigError", "CreateContainerError",
           "RunContainerError", "CrashLoopBackOff", "OOMKilled", "Error", "Completed",
           "StartError", "OutOfcpu", "OutOfmemory", "OutOfpods", "Evicted"}
API_REASONS = {"Passed", "ServiceNotFound", "ServicePortError", "ServiceAccessError",
               "EndpointsNotFound", "MissingEndpoints", "EndpointsAccessError", "FailedDiscoveryCheck"}


def category(value, choices):
    return value if isinstance(value, str) and value in choices else "other"


def object_fields(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, "duplicate diagnostic field")
        value[key] = item
    return value


def pod_status(pod):
    require(isinstance(pod, dict), "invalid diagnostic Pod")
    status = pod.get("status", {})
    require(isinstance(status, dict), "invalid diagnostic Pod status")
    containers = status.get("containerStatuses", [])
    require(isinstance(containers, list) and len(containers) <= 16, "invalid diagnostic container count")
    return status, containers


def container_state(container, waiting, terminated):
    require(isinstance(container, dict), "invalid diagnostic container")
    state = container.get("state", {})
    require(isinstance(state, dict), "invalid diagnostic container state")
    for key, counts in (("waiting", waiting), ("terminated", terminated)):
        if key not in state:
            continue
        require(isinstance(state[key], dict), "invalid diagnostic state detail")
        counts[category(state[key].get("reason"), REASONS)] += 1
    return container.get("ready") is True


def api_availability(document):
    unavailable = {"state": "unreported", "reason": "other"}
    if document is None:
        return unavailable
    require(isinstance(document, dict), "invalid diagnostic APIService")
    status = document.get("status", {})
    require(isinstance(status, dict), "invalid diagnostic APIService status")
    conditions = status.get("conditions", [])
    require(isinstance(conditions, list) and len(conditions) <= 8, "invalid diagnostic conditions")
    require(all(isinstance(c, dict) for c in conditions), "invalid diagnostic condition")
    available = [c for c in conditions if c.get("type") == "Available"]
    require(len(available) <= 1, "ambiguous diagnostic availability")
    if not available:
        return unavailable
    return {"state": category(available[0].get("status"), {"True", "False", "Unknown"}),
            "reason": category(available[0].get("reason"), API_REASONS)}


def summarise(document, api_service=None):
    require(isinstance(document, dict), "invalid diagnostic list")
    pods = document.get("items")
    require(isinstance(pods, list) and len(pods) <= 64, "invalid diagnostic Pod count")
    phases, reasons, waiting, terminated = (Counter() for _ in range(4))
    ready = total = missing = 0
    for pod in pods:
        status, containers = pod_status(pod)
        phases[category(status.get("phase"), PHASES)] += 1
        reasons[category(status.get("reason"), REASONS)] += 1
        missing += "containerStatuses" not in status
        total += len(containers)
        ready += sum(container_state(c, waiting, terminated) for c in containers)
    result = {"schemaVersion": 1, "scope": "local-readiness-diagnostic", "qualified": False,
              "podCount": len(pods), "containerStatuses": total,
              "readyContainers": ready, "missingContainerStatusPods": missing,
              "phases": dict(phases), "podReasons": dict(reasons),
              "waitingReasons": dict(waiting), "terminatedReasons": dict(terminated),
              "apiServiceAvailability": api_availability(api_service)}
    privacy(result)
    return result


def read_input(path):
    with path.open("rb") as source:
        data = source.read(MAX_BYTES + 1)
    require(len(data) <= MAX_BYTES, "readiness input exceeds byte limit")
    return json.loads(data, object_pairs_hook=object_fields)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True)
    parser.add_argument("--api-service", type=Path)
    args = parser.parse_args()
    try:
        api_service = read_input(args.api_service) if args.api_service else None
        result = summarise(read_input(args.input), api_service)
        write_new(args.output, result)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ContractError, OSError, ValueError, TypeError, RecursionError):
        print("Cannot retain bounded readiness diagnostic", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
