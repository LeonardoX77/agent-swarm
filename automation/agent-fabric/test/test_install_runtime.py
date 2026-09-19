import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
LIBRARY = ROOT / 'lib' / 'install_runtime.py'


def module():
    spec = importlib.util.spec_from_file_location('install_runtime_test', LIBRARY)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class InstallRuntimeTests(unittest.TestCase):
    def test_plan_is_non_mutating_and_includes_exact_restricted_key_line(self):
        installer = module()
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / 'home'
            key = Path(directory) / 'peer.pub'
            key.write_text('ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest peer\n', encoding='utf-8')
            plan = installer.plan(ROOT, home, 'macbook', key)
        self.assertFalse(home.exists())
        self.assertEqual(plan['host_config'], str(home / '.local/agent-fabric/config/host.json'))
        self.assertEqual(
            plan['authorized_keys_line'],
            f'restrict,command="{home}/.local/agent-fabric/bin/fabric-runner --config {home}/.local/agent-fabric/config/host.json" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest peer',
        )

    def test_apply_installs_only_runtime_files_under_home_and_revert_removes_them(self):
        installer = module()
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / 'home'
            key = Path(directory) / 'peer.pub'
            key.write_text('ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest peer\n', encoding='utf-8')
            with patch.object(installer, 'effective_user', return_value='jarvis'):
                result = installer.apply(ROOT, home, 'mac-mini', key)
            runtime = home / '.local/agent-fabric'
            self.assertEqual(result['runtime_root'], str(runtime))
            self.assertTrue((runtime / 'bin/fabric-runner').is_file())
            self.assertTrue((runtime / 'bin/fabric-dispatch').is_file())
            self.assertTrue((runtime / 'bin/fabric-host-preflight').is_file())
            self.assertTrue((runtime / 'bin/fabric-activity').is_file())
            self.assertTrue((runtime / 'lib/ssh_policy.py').is_file())
            config = json.loads((runtime / 'config/host.json').read_text(encoding='utf-8'))
            self.assertEqual(config['role'], 'mac-mini')
            self.assertTrue(os.access(runtime / 'bin/fabric-runner', os.X_OK))
            self.assertEqual(installer.revert(home), {'reverted': True})
            self.assertFalse(runtime.exists())

    def test_apply_rejects_user_that_does_not_match_role_without_writing(self):
        installer = module()
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / 'home'
            key = Path(directory) / 'peer.pub'
            key.write_text('ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest peer\n', encoding='utf-8')
            with patch.object(installer, 'effective_user', return_value='jarvis'):
                with self.assertRaisesRegex(ValueError, 'UNEXPECTED_USER'):
                    installer.apply(ROOT, home, 'macbook', key)
            self.assertFalse(home.exists())

    def test_rejects_unknown_role_and_multiline_peer_key(self):
        installer = module()
        with tempfile.TemporaryDirectory() as directory:
            key = Path(directory) / 'peer.pub'
            key.write_text('ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest peer\nextra', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'INVALID_HOST_ROLE'):
                installer.plan(ROOT, Path(directory) / 'home', 'other', key)
            with self.assertRaisesRegex(ValueError, 'INVALID_PUBLIC_KEY'):
                installer.plan(ROOT, Path(directory) / 'home', 'macbook', key)


if __name__ == '__main__':
    unittest.main()
