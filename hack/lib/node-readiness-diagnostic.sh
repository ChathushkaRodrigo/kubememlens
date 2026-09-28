#!/usr/bin/env bash

# Called only before cleanup of the verifier's owned disposable kind cluster.
# Raw API responses remain private and are removed by the existing cleanup.
# shellcheck disable=SC2154
node_context_readiness_failure() {
  local pods="${work_dir}/readiness-pods.private.json"
  local api="${work_dir}/readiness-api.private.json"
  if ! kctl get pods --all-namespaces --request-timeout=5s -o json > "${pods}" 2> "${work_dir}/readiness-pods.private.log"; then
    return 1
  fi
  local args=(--input "${pods}" --output "${artifact_dir}/readiness-failure.json")
  if kctl get apiservice v1alpha1.memory.kubememlens.io --ignore-not-found --request-timeout=5s -o json > "${api}" 2> "${work_dir}/readiness-api.private.log" && [ -s "${api}" ]; then
    args+=(--api-service "${api}")
  fi
  python3 hack/node-qualification/readiness_failure.py "${args[@]}"
}
