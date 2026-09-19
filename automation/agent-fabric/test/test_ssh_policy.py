import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from ssh_policy import authorized_keys_line, validate_authorized_keys_line


class SshPolicyTests(unittest.TestCase):
    def test_builds_exact_restricted_forced_command_line(self):
        line = authorized_keys_line(
            '/usr/local/libexec/fabric-runner',
            '/etc/agent-fabric/host.json',
            'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest fabric',
        )
        self.assertEqual(line, 'restrict,command="/usr/local/libexec/fabric-runner --config /etc/agent-fabric/host.json" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest fabric')
        self.assertTrue(validate_authorized_keys_line(line))

    def test_rejects_relative_or_injected_values(self):
        with self.assertRaises(ValueError):
            authorized_keys_line('bin/fabric-runner', '/etc/agent-fabric/host.json', 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest')
        self.assertFalse(validate_authorized_keys_line('command="/runner --config /config" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest'))


if __name__ == '__main__':
    unittest.main()
