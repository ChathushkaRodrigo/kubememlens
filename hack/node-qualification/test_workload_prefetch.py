"""The local fixture must be fetched before rollout and measurement."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'hack/lib/node-qualification-kind.sh'
SCRIPT = r'''
set -Eeuo pipefail
source "$1"
source hack/lib/node-context-fixture.sh
work_dir=$2
artifact_dir=$2
kubeconfig=fixture
cluster=kube-memlens-node-context-test
node=kube-memlens-node-context-test-control-plane
node_image=kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
NODE_CONTEXT_QUALIFICATION_PROFILE=hack/node-qualification/profiles/kind-137.json
failures=$3
cached=$4
pulls=0
python3() {
  if [ "$1" = hack/node-qualification/check_resource_ownership.py ]; then return 0; fi
  command python3 "$@"
}
sleep() { :; }
docker() {
  case "$*" in
    *' crictl inspecti '*) printf 'inspect %s\n' "$*" >> "$work_dir/events"; [ "$cached" = true ] ;;
    *' crictl pull '*)
      printf 'pull %s\n' "$*" >> "$work_dir/events"
      pulls=$((pulls + 1))
      [ "$pulls" -gt "$failures" ] ;;
    *) return 99 ;;
  esac
}
kctl() { printf 'kctl %s\n' "$*" >> "$work_dir/events"; }
node_qualification_measure() { printf 'measure %s\n' "$1" >> "$work_dir/events"; }
node_qualification_baseline
'''


class WorkloadPrefetchTests(unittest.TestCase):
    def exercise(self, failures, cached=False):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(['bash', '-c', SCRIPT, 'fixture', str(HELPER), directory,
                                     str(failures), str(cached).lower()], cwd=ROOT, capture_output=True, text=True, timeout=10)
            events = (Path(directory) / 'events').read_text().splitlines()
        return result, events

    def test_cached_pinned_image_does_not_require_registry_access(self):
        result, events = self.exercise(3, cached=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(e.startswith('pull ') for e in events))
        self.assertTrue(events[0].startswith('inspect '))
        self.assertEqual(events[-1], 'measure baseline')

    def test_ready_image_precedes_rollout_and_measurement(self):
        result, events = self.exercise(0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len([e for e in events if e.startswith('pull ')]), 1)
        self.assertIn('timeout 30s crictl pull docker.io/library/busybox@sha256:', events[1])
        self.assertTrue(events[2].startswith('kctl apply '))
        self.assertEqual(events[-1], 'measure baseline')

    def test_transient_registry_failure_retries_before_rollout(self):
        result, events = self.exercise(2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(all(e.startswith('pull ') for e in events[1:4]))
        self.assertTrue(events[4].startswith('kctl apply '))
        self.assertEqual(events[-1], 'measure baseline')

    def test_exhausted_registry_attempts_prevent_rollout_and_measurement(self):
        result, events = self.exercise(3)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(events), 4)
        self.assertTrue(all(e.startswith('pull ') for e in events[1:]))
        self.assertIn('bounded preflight', result.stderr)


if __name__ == '__main__':
    unittest.main()
