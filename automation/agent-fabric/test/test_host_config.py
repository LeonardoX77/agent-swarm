import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / 'lib'))
from host_config import load_config


VALID = {
    'version': 1,
    'role': 'macbook',
    'expected_user': 'leo',
    'max_timeout_seconds': 60,
    'workspace_roots': {'mac-agent-fabric': '/tmp/workspace'},
    'ssh_aliases': {},
    'allowed_runtimes': ['pi', 'opencode', 'claude'],
}


class HostConfigTests(unittest.TestCase):
    def test_accepts_non_empty_unique_closed_runtime_allowlist(self):
        self.assertEqual(load_config(VALID), VALID)

    def test_rejects_missing_empty_duplicate_or_unknown_runtime_allowlists(self):
        for change in (
            {'allowed_runtimes': []},
            {'allowed_runtimes': ['pi', 'pi']},
            {'allowed_runtimes': ['unknown']},
        ):
            with self.assertRaises(ValueError):
                load_config({**VALID, **change})
        missing = {key: value for key, value in VALID.items() if key != 'allowed_runtimes'}
        with self.assertRaises(ValueError):
            load_config(missing)


if __name__ == '__main__':
    unittest.main()
