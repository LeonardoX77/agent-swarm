import importlib.machinery
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
CLI = ROOT / 'bin' / 'fabric-host-preflight'


def module():
    loader = importlib.machinery.SourceFileLoader('fabric_preflight_test', str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    value = importlib.util.module_from_spec(spec)
    loader.exec_module(value)
    return value


class HostPreflightTests(unittest.TestCase):
    def test_reports_valid_without_mutating_host(self):
        preflight = module()
        with tempfile.TemporaryDirectory() as directory:
            config = {'version': 1, 'role': 'macbook', 'expected_user': 'leo', 'max_timeout_seconds': 60, 'workspace_roots': {'mac-agent-fabric': directory}, 'ssh_aliases': {}}
            with patch.object(preflight.getpass, 'getuser', return_value='leo'), patch.object(preflight.shutil, 'which', return_value='/fake/bin'):
                self.assertEqual(preflight.preflight(config), [])

    def test_reports_missing_workspace_and_wrong_user(self):
        preflight = module()
        config = {'version': 1, 'role': 'macbook', 'expected_user': 'leo', 'max_timeout_seconds': 60, 'workspace_roots': {'mac-agent-fabric': '/missing'}, 'ssh_aliases': {}}
        with patch.object(preflight.getpass, 'getuser', return_value='other'), patch.object(preflight.shutil, 'which', return_value='/fake/bin'):
            diagnostics = preflight.preflight(config)
        self.assertIn('EXPECTED_USER_MISMATCH', diagnostics)
        self.assertIn('WORKSPACE_UNAVAILABLE', diagnostics)


if __name__ == '__main__':
    unittest.main()
