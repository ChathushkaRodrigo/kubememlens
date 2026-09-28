import json
from pathlib import Path
import tempfile
import unittest

from common import ContractError, MAX_BYTES
from readiness_failure import read_input, summarise


class ReadinessFailureTests(unittest.TestCase):
    def test_waiting_and_terminal_reasons_are_counted_without_identity(self):
        document = {"items": [
            {"metadata": {"name": "private-workload", "namespace": "private-tenant"},
             "status": {"phase": "Pending", "containerStatuses": [
                 {"name": "private-container", "ready": False,
                  "state": {"waiting": {"reason": "ImagePullBackOff", "message": "private-registry-token"}}}]}},
            {"status": {"phase": "Running", "containerStatuses": [
                {"ready": True, "state": {"running": {}}},
                {"ready": False, "state": {"terminated": {"reason": "OOMKilled", "message": "private-path"}}}]}}
        ]}
        result = summarise(document)
        self.assertEqual(result["waitingReasons"], {"ImagePullBackOff": 1})
        self.assertEqual(result["terminatedReasons"], {"OOMKilled": 1})
        self.assertEqual(result["readyContainers"], 1)
        self.assertEqual(result["containerStatuses"], 3)
        self.assertFalse(result["qualified"])
        self.assertNotIn("private", json.dumps(result))

    def test_missing_and_unknown_status_are_visible_without_raw_text(self):
        result = summarise({"items": [{"status": {"phase": "sensitive-value"}}, {}]})
        self.assertEqual(result["phases"], {"other": 2})
        self.assertEqual(result["missingContainerStatusPods"], 2)
        self.assertNotIn("sensitive", json.dumps(result))

    def test_unknown_container_reason_is_not_copied(self):
        result = summarise({"items": [{"status": {"containerStatuses": [
            {"state": {"waiting": {"reason": "secret endpoint"}}}]}}]})
        self.assertEqual(result["waitingReasons"], {"other": 1})

    def test_api_availability_retains_only_known_reason(self):
        api = {"metadata": {"name": "private-service"}, "status": {"conditions": [
            {"type": "Available", "status": "False", "reason": "FailedDiscoveryCheck",
             "message": "private-server-address-and-credentials"}]}}
        result = summarise({"items": []}, api)
        self.assertEqual(result["apiServiceAvailability"], {"state": "False", "reason": "FailedDiscoveryCheck"})
        self.assertNotIn("private", json.dumps(result))
        self.assertEqual(summarise({"items": []})["apiServiceAvailability"]["state"], "unreported")
        self.assertEqual(summarise({"items": []}, {})["apiServiceAvailability"]["state"], "unreported")
        api["status"]["conditions"][0]["reason"] = "private-value"
        self.assertEqual(summarise({"items": []}, api)["apiServiceAvailability"]["reason"], "other")

    def test_malformed_and_oversized_inputs_fail(self):
        for document in [[], {}, {"items": [None]}, {"items": [{}] * 65},
                         {"items": [{"status": {"containerStatuses": [{}] * 17}}]},
                         {"items": [{"status": {"containerStatuses": [{"state": None}]}}]}]:
            with self.subTest(document=document), self.assertRaises(ContractError):
                summarise(document)
        for api in [[], {"status": None}, {"status": {"conditions": [None]}},
                    {"status": {"conditions": [{"type": "Available"}] * 2}}]:
            with self.subTest(api=api), self.assertRaises(ContractError):
                summarise({"items": []}, api)

    def test_raw_input_rejects_duplicate_fields_and_oversized_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            for content in [b'{"items":[],"items":[]}', b" " * (MAX_BYTES + 1)]:
                path.write_bytes(content)
                with self.assertRaises(ContractError):
                    read_input(path)


if __name__ == "__main__":
    unittest.main()
