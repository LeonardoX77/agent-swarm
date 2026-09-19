import hashlib
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).parents[1] / 'bin' / 'fabric-activity'
EVENT = {
    'agent_id': 'writer-alice',
    'repository_id': 'example/repository',
    'host_id': 'macbook.local',
    'operation_id': 'op-123',
    'area': 'automation',
    'outcome': 'completed',
}


class ActivityCliTests(unittest.TestCase):
    def run_cli(self, record, event=EVENT):
        return subprocess.run(
            [sys.executable, str(CLI), '--record', str(record)],
            input=json.dumps(event), text=True, capture_output=True,
        )

    def test_records_hashed_sanitized_jsonl_event(self):
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / 'activity.jsonl'
            result = self.run_cli(record)
            self.assertEqual(result.returncode, 0)
            stored = json.loads(record.read_text())
            self.assertEqual(stored['agent_id_sha256'], hashlib.sha256(b'writer-alice').hexdigest())
            self.assertEqual(stored['repository_id_sha256'], hashlib.sha256(b'example/repository').hexdigest())
            self.assertEqual(stored['host_id_sha256'], hashlib.sha256(b'macbook.local').hexdigest())
            self.assertEqual(stored['operation_id'], 'op-123')
            self.assertEqual(stored['area'], 'automation')
            self.assertEqual(stored['outcome'], 'completed')
            self.assertNotIn('agent_id', stored)
            self.assertNotIn('repository_id', stored)
            self.assertNotIn('host_id', stored)

    def test_rejects_secrets_and_does_not_disclose_them(self):
        with tempfile.TemporaryDirectory() as directory:
            event = {**EVENT, 'token': 'super-secret-value'}
            result = self.run_cli(Path(directory) / 'activity.jsonl', event)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout.strip(), 'INVALID_ACTIVITY_EVENT')
            self.assertNotIn('super-secret-value', result.stderr)

    def test_rejects_unsafe_destination_without_disclosing_path(self):
        result = self.run_cli('/Volumes/team-share/secret-activity.jsonl')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout.strip(), 'UNSAFE_RECORD_DESTINATION')
        self.assertNotIn('/Volumes/team-share', result.stderr)

    def test_rejects_invalid_json_without_traceback(self):
        result = subprocess.run(
            [sys.executable, str(CLI), '--record', '/tmp/activity.jsonl'],
            input='{', text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout.strip(), 'INVALID_ACTIVITY_EVENT')
        self.assertNotIn('Traceback', result.stderr)

    def test_allows_optional_area_to_be_omitted_and_creates_owner_only_record(self):
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / 'activity.jsonl'
            result = self.run_cli(record, {key: value for key, value in EVENT.items() if key != 'area'})
            self.assertEqual(result.returncode, 0)
            self.assertNotIn('area', json.loads(record.read_text()))
            self.assertEqual(stat.S_IMODE(record.stat().st_mode), 0o600)

    def test_rejects_mount_and_relative_destinations(self):
        for destination in ('activity.jsonl', '/mnt/shared/activity.jsonl'):
            result = self.run_cli(destination)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout.strip(), 'UNSAFE_RECORD_DESTINATION')
            self.assertNotIn(destination, result.stderr)


if __name__ == '__main__':
    unittest.main()
