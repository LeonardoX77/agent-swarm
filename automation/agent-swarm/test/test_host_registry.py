import json
import os
import subprocess
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
        'macbook': {'hostname_prefix': 'MacBookLeo', 'role': 'hub', 'ssh_alias': 'swarm-macbook', 'address': 'MacBookLeo.local', 'catalog_root': '/Users/leo/projects', 'repo': '/Users/leo/projects/leo/mac-agent-swarm', 'path': '/opt/homebrew/bin:/usr/bin:/bin', 'gui_cwd': '/Users/leo/tmp', 'runtimes': ['pi', 'claude']},
        'mac-mini': {'hostname_prefix': 'MacMiniLeo', 'role': 'spoke', 'ssh_alias': 'swarm-mac-mini', 'address': 'MacMiniLeo.local', 'catalog_root': '/Volumes/agent-projects', 'repo': '/Volumes/agent-projects/leo/mac-agent-swarm', 'path': '/opt/homebrew/bin:/usr/bin:/bin', 'gui_cwd': '/Users/leo/tmp', 'runtimes': ['pi']},
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

    def test_catalog_mode_defaults_to_smb_and_rejects_unknown_modes(self):
        self.assertEqual(HostRegistry(self.write(VALID)).get('mac-mini').get('catalog_mode', 'smb'), 'smb')
        local = {**VALID, 'hosts': {**VALID['hosts'], 'mac-mini': {**VALID['hosts']['mac-mini'], 'catalog_mode': 'local'}}}
        self.assertEqual(HostRegistry(self.write(local)).get('mac-mini')['catalog_mode'], 'local')
        invalid = {**local, 'hosts': {**local['hosts'], 'mac-mini': {**local['hosts']['mac-mini'], 'catalog_mode': 'unknown'}}}
        with self.assertRaises(RegistryError):
            HostRegistry(self.write(invalid))

    def test_local_catalog_registry_rejects_paths_outside_root_and_share_hosts(self):
        base = {**VALID['hosts']['mac-mini'], 'catalog_mode': 'local',
                'catalog_root': '/srv/projects', 'repo': '/srv/projects/agent-swarm'}
        for changes in ({'repo': '/srv/other/agent-swarm'}, {'repo': '/srv/projects'},
                        {'repo': '/srv/projects/../other/agent-swarm'},
                        {'share_hosts': ['share.example.test']}):
            with self.subTest(changes=changes):
                host = {**base, **changes}
                value = {**VALID, 'hosts': {**VALID['hosts'], 'mac-mini': host}}
                path = self.write(value)
                before = path.read_bytes()
                with self.assertRaisesRegex(RegistryError, '^INVALID_HOST_REGISTRY$'):
                    HostRegistry(path)
                self.assertEqual(path.read_bytes(), before)

    def test_optional_candidate_lists_are_preserved_and_validated(self):
        value = {**VALID, 'hosts': {**VALID['hosts'], 'mac-mini': {**VALID['hosts']['mac-mini'], 'fallback_addresses': ['100.64.0.2'], 'share_hosts': ['MacBookLeo.local', '192.168.1.2']}}}
        self.assertEqual(HostRegistry(self.write(value)).get('mac-mini')['fallback_addresses'], ['100.64.0.2'])
        for key, entries in (('fallback_addresses', []), ('fallback_addresses', ['MacMiniLeo.local']), ('fallback_addresses', ['bad address']), ('fallback_addresses', ['-x']), ('fallback_addresses', ['--help']), ('fallback_addresses', ['-oProxyCommand']), ('share_hosts', []), ('share_hosts', ['same', 'same']), ('share_hosts', ['-x']), ('share_hosts', ['--help']), ('share_hosts', ['-oProxyCommand'])):
            with self.subTest(key=key, entries=entries):
                invalid = {**value, 'hosts': {**value['hosts'], 'mac-mini': {**value['hosts']['mac-mini'], key: entries}}}
                with self.assertRaises(RegistryError): HostRegistry(self.write(invalid))

    def test_rejects_schema_and_host_validation_errors(self):
        cases = [
            {**VALID, 'extra': 1},
            {**VALID, 'version': 2},
            {**VALID, 'hub': 'missing'},
            {**VALID, 'share': {**VALID['share'], 'extra': 'x'}},
            {**VALID, 'hosts': {**VALID['hosts'], 'bad_name': VALID['hosts']['macbook']}},
            {**VALID, 'hosts': {**VALID['hosts'], 'macbook': {**VALID['hosts']['macbook'], 'role': 'spoke'}}},
            {**VALID, 'hosts': {**VALID['hosts'], 'macbook': {k: v for k, v in VALID['hosts']['macbook'].items() if k != 'address'}}},
            {**VALID, 'hosts': {**VALID['hosts'], 'macbook': {**VALID['hosts']['macbook'], 'address': 'bad address'}}},
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

    def test_real_hostname_prefixes_match_in_any_case(self):
        nodes = (os.uname().nodename, subprocess.run(
            ['hostname', '-s'], check=True, text=True, capture_output=True).stdout.strip())
        for node in (*nodes, 'MacMiniLeo', 'StraßeHost'):
            short = node.split('.')[0]
            for prefix in (short, short.lower(), short.upper()):
                with self.subTest(node=node, prefix=prefix):
                    host = {**VALID['hosts']['macbook'], 'hostname_prefix': prefix}
                    value = {**VALID, 'hosts': {'macbook': host}}
                    registry = HostRegistry(self.write(value))
                    for name in (node, short + '.example.test'):
                        self.assertEqual(registry.self_host(name)['name'], 'macbook')
                    self.assertIsNone(registry.self_host('unrelated-' + node))
                    self.assertIsNone(registry.self_host(None))

    def test_rejects_casefolded_duplicate_and_overlapping_prefixes(self):
        for prefix in ('macbookleo', 'MACBOOKLEO-mini', 'macbook'):
            with self.subTest(prefix=prefix):
                value = {**VALID, 'hosts': {**VALID['hosts'], 'mac-mini': {
                    **VALID['hosts']['mac-mini'], 'hostname_prefix': prefix}}}
                path = self.write(value)
                before = path.read_bytes()
                with self.assertRaisesRegex(RegistryError, '^INVALID_HOST_REGISTRY$'):
                    HostRegistry(path)
                self.assertEqual(path.read_bytes(), before)

    def test_example_registry_validates_and_is_generic(self):
        example = Path(__file__).parents[3] / 'config' / 'hosts.example.json'
        registry = HostRegistry(example)
        self.assertEqual(registry.hub, 'hub-mac')
        self.assertEqual(registry.get('spoke-mac')['role'], 'spoke')
        self.assertEqual(registry.get('hub-mac')['ssh_alias'], 'swarm-hub-mac')
        self.assertNotRegex(example.read_text(encoding='utf-8'), r'(?i)leo|bea|macbook|mac-mini|192\.168\.')


if __name__ == '__main__':
    unittest.main()
