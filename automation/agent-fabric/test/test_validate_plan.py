import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from validate_plan import validate_plan


def plan():
    return {
        'schema_version': 1,
        'macbook': {
            'ssh_host_alias': 'agent-fabric-macbook',
            'workspace_share_root': '/Users/leo/projects',
            'future_share_name': 'agent-workspaces',
        },
        'mac_mini': {
            'ssh_host_alias': 'agent-fabric-macbook',
            'future_mount_target': '/Volumes/agent-workspaces',
            'execution_identity': 'fabric-runner',
        },
        'workspace_areas': [{'id': 'coding-agent', 'relative_path': 'packages/coding-agent'}],
        'skills': {
            'transport': 'git',
            'repository_url': 'https://example.invalid/org/shared-skills.git',
            'local_clone_roots': {'macbook': '/opt/agent-fabric/skills', 'mac_mini': '/opt/agent-fabric/skills'},
        },
    }


class ValidatePlanTests(unittest.TestCase):
    def test_valid_plan_has_no_diagnostics(self):
        self.assertEqual(validate_plan(plan()), [])

    def test_lock_root_is_obsolete_and_rejected_as_unknown(self):
        candidate = plan()
        candidate['macbook']['lock_root'] = '/Users/Shared/agent-fabric/locks'
        self.assertEqual({item['code'] for item in validate_plan(candidate)}, {'UNKNOWN_FIELD'})

    def test_rejects_unsafe_share_and_mount_roots(self):
        for field, value in [('workspace_share_root', '/Users/leo'), ('future_mount_target', '/Users/mini/mount')]:
            candidate = plan()
            target = candidate['macbook'] if field == 'workspace_share_root' else candidate['mac_mini']
            target[field] = value
            diagnostics = validate_plan(candidate)
            self.assertEqual(diagnostics[0]['code'], 'PROTECTED_PATH')

    def test_rejects_credentials_unknown_fields_and_bad_skills(self):
        candidate = plan()
        candidate['password'] = 'do-not-print'
        candidate['skills']['transport'] = 'smb'
        diagnostics = validate_plan(candidate)
        self.assertEqual({item['code'] for item in diagnostics}, {'CREDENTIAL_FIELD', 'INVALID_TRANSPORT', 'UNKNOWN_FIELD'})
        self.assertNotIn('do-not-print', json.dumps(diagnostics))

    def test_rejects_placeholder_areas_and_overlap(self):
        candidate = plan()
        candidate['mac_mini']['execution_identity'] = '<future-account>'
        candidate['workspace_areas'].append({'id': 'other', 'relative_path': 'packages'})
        diagnostics = validate_plan(candidate)
        self.assertEqual({item['code'] for item in diagnostics}, {'PLACEHOLDER_IDENTITY', 'AREA_OVERLAP'})

    def test_rejects_symlinked_clone_roots_without_following_them(self):
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / 'clone-root'
            os.symlink(Path(directory) / 'missing-target', link)
            candidate = plan()
            candidate['skills']['local_clone_roots'] = {'macbook': str(link), 'mac_mini': str(link)}
            diagnostics = validate_plan(candidate)
            self.assertIn('AMBIGUOUS_PATH', {item['code'] for item in diagnostics})


if __name__ == '__main__':
    unittest.main()
