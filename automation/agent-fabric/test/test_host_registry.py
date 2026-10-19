import json
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parents[1] / 'lib'))
from host_registry import HostRegistry, RegistryError


VALID = {
    'version': 1,
    'hub': 'macbook',
    'share': {'host': 'MacBookLeo.local', 'name': 'agent-projects', 'user': 'leo'},
    'hosts': {
        'macbook': {'hostname_prefix': 'MacBookLeo', 'role': 'hub', 'ssh_alias': 'fabric-macbook', 'catalog_root': '/Users/leo/projects', 'repo': '/Users/leo/projects/leo/mac-agent-fabric', 'path': '/opt/homebrew/bin:/usr/bin:/bin', 'gui_cwd': '/Users/leo/tmp', 'runtimes': ['pi', 'claude']},
        'mac-mini': {'hostname_prefix': 'MacMiniLeo', 'role': 'spoke', 'ssh_alias': 'fabric-mac-mini', 'catalog_root': '/Volumes/agent-projects', 'repo': '/Volumes/agent-projects/leo/mac-agent-fabric', 'path': '/opt/homebrew/bin:/usr/bin:/bin', 'gui_cwd': '/Users/leo/tmp', 'runtimes': ['pi']},
    },
}


class HostRegistryTests(unittest.TestCase):
    def write(self, value):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / 'hosts.json'
        path.write_text(json.dumps(value), encoding='utf-8')
        self.addCleanup(directory.cleanup)
        return path

    def test_valid_file_loads_gets_hosts_and_detects_self(self):
        registry = HostRegistry(self.write(VALID))
        self.assertEqual(registry.get('macbook')['role'], 'hub')
        self.assertEqual(registry.self_host('MacMiniLeo.local')['name'], 'mac-mini')
        self.assertIsNone(registry.self_host('OtherMac'))

    def test_rejects_schema_and_host_validation_errors(self):
        cases = [
            {**VALID, 'extra': 1},
            {**VALID, 'version': 2},
            {**VALID, 'hub': 'missing'},
            {**VALID, 'share': {**VALID['share'], 'extra': 'x'}},
            {**VALID, 'hosts': {**VALID['hosts'], 'bad_name': VALID['hosts']['macbook']}},
            {**VALID, 'hosts': {**VALID['hosts'], 'macbook': {**VALID['hosts']['macbook'], 'role': 'spoke'}}},
            {**VALID, 'hosts': {**VALID['hosts'], 'macbook': {**VALID['hosts']['macbook'], 'catalog_root': 'relative'}}},
            {**VALID, 'hosts': {**VALID['hosts'], 'macbook': {**VALID['hosts']['macbook'], 'runtimes': ['claude']}}},
            {**VALID, 'hosts': {**VALID['hosts'], 'macbook': {**VALID['hosts']['macbook'], 'hostname_prefix': 'Mac'}}},
        ]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(RegistryError):
                HostRegistry(self.write(value))

    def test_rejects_prefixes_that_overlap(self):
        value = {**VALID, 'hosts': {**VALID['hosts'], 'mac-mini': {**VALID['hosts']['mac-mini'], 'hostname_prefix': 'MacBookLeo-mini'}}}
        with self.assertRaises(RegistryError):
            HostRegistry(self.write(value))

    def test_real_registry_validates(self):
        registry = HostRegistry()
        self.assertEqual(registry.get('mac-mini')['ssh_alias'], 'fabric-mac-mini')


if __name__ == '__main__':
    unittest.main()
