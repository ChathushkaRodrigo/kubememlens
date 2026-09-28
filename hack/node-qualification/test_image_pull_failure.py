import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from image_pull_failure import classify


class ImagePullFailureTests(unittest.TestCase):
    def test_known_failures_only_return_fixed_categories(self):
        cases = {
            '429 Too Many Requests at https://private.invalid/token': 'rate-limited',
            'unexpected status: 403 Forbidden, private credential': 'registry-denied',
            'manifest unknown: private/image': 'image-not-found',
            'no match for platform in manifest': 'platform-unavailable',
            'lookup private.invalid: no such host': 'dns-unavailable',
            'x509: certificate signed by unknown authority': 'tls-failure',
            'rpc error: DeadlineExceeded: context deadline exceeded': 'transport-timeout',
            'unexpected status: 503 Service Unavailable': 'registry-unavailable',
            "timeout: failed to run command 'private': No such file or directory": 'local-command-unavailable',
            'private value without a recognised failure': 'unclassified',
        }
        for message, expected in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(classify(message), expected)

    def test_cli_never_copies_private_or_oversized_input(self):
        script = Path(__file__).with_name('image_pull_failure.py')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'private.log'
            for data, expected in [(b'403 Forbidden private-token', 'registry-denied'),
                                   (b'403 Forbidden ' + b'x' * 65536, 'unclassified')]:
                path.write_bytes(data)
                result = subprocess.run(['python3', str(script), str(path)], check=True,
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(json.loads(result.stdout), {
                    'scope': 'fixture-image-preflight', 'qualified': False, 'failureClass': expected})
                self.assertEqual(result.stderr, '')


if __name__ == '__main__':
    unittest.main()
