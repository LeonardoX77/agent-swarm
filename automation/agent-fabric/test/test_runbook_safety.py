import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
RUNBOOKS = ROOT / 'docs' / 'runbooks' / 'agent-fabric'


class RunbookSafetyTests(unittest.TestCase):
    def test_v1_runbooks_cover_the_operator_contract(self):
        required = {
            'operation.md': (
                '## Camino rápido', 'MacBook → Mac mini', 'Mac mini → MacBook',
                '## Mapeo de workspaces', '## Resultado acotado',
                '## Actividad y concurrencia', 'No hay locks', '## Fallas',
            ),
            'validation.md': (
                '## Checklist ordenado', 'solo lectura', 'cambio activo',
                'SMB', 'comando forzado', 'huella', 'MacBook → Mac mini',
                'Mac mini → MacBook', 'LAN', 'Tailscale', 'secretos',
            ),
            'rollback.md': (
                '## Antes de revertir', 'runtime', 'authorized_keys',
                'login item', 'agent-projects', 'Remote Login', 'Nunca elimines',
            ),
        }
        for name, fragments in required.items():
            content = (RUNBOOKS / name).read_text(encoding='utf-8')
            for fragment in fragments:
                self.assertIn(fragment.lower(), content.lower(), f'{name}: {fragment}')

    def test_example_is_safe_and_valid_request_shape(self):
        request = json.loads((ROOT / 'automation' / 'agent-fabric' / 'examples' / 'task-request.example.json').read_text(encoding='utf-8'))
        self.assertEqual(1, request['version'])
        self.assertEqual('macbook', request['initiator'])
        self.assertEqual('.', request['relative_path'])
        self.assertLessEqual(request['timeout_seconds'], 900)
        self.assertNotIn('password', json.dumps(request).lower())

    def test_macbook_setup_uses_explicit_safe_smb_flags(self):
        content = (ROOT / 'docs' / 'setup' / 'macbook.md').read_text(encoding='utf-8')
        self.assertIn(
            'sharing -a /Users/leo/projects -S agent-projects -s 001 -g 000 -R 0',
            content,
        )

    def test_docs_reject_obsolete_or_unsafe_operations(self):
        content = '\n'.join([
            (ROOT / 'README.md').read_text(encoding='utf-8'),
            *((RUNBOOKS / name).read_text(encoding='utf-8') for name in ('operation.md', 'validation.md', 'rollback.md')),
        ])
        forbidden = (
            'fabric-lock', 'agent-workspaces', '/Volumes/agent-workspaces',
            'fabric-plan', '--apply', 'password=', 'PasswordAuthentication yes',
            'ssh -R', 'ssh -L', 'sudo ssh', 'ssh sudo', 'router port forwarding',
        )
        for value in forbidden:
            self.assertNotIn(value.lower(), content.lower(), value)
        self.assertIsNone(re.search(r'^\s*(?:ssh\s+[^\n]*\s+)?sudo\b', content, re.MULTILINE))


if __name__ == '__main__':
    unittest.main()
