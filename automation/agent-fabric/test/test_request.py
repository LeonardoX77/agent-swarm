import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / 'lib'))
from request import validate_request


VALID = {
    'version': 1,
    'request_id': '550e8400-e29b-41d4-a716-446655440000',
    'workspace': 'mac-agent-fabric',
    'relative_path': '.',
    'prompt': 'Inspect focused findings.',
    'runtime': 'pi',
    'initiator': 'macbook',
    'timeout_seconds': 30,
}


class RequestTests(unittest.TestCase):
    def test_accepts_exact_v1_request(self):
        self.assertEqual(validate_request(VALID), VALID)

    def test_rejects_unknown_fields_secrets_unsafe_paths_and_unknown_runtimes(self):
        for change in ({'extra': True}, {'token': 'secret'}, {'relative_path': '../escape'}, {'relative_path': '/absolute'}, {'runtime': 'unknown'}):
            with self.assertRaises(ValueError):
                validate_request({**VALID, **change})


if __name__ == '__main__':
    unittest.main()
