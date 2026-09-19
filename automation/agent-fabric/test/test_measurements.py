import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'lib'))
from measurements import build_measurement, adjustment_ready


REQUIRED_OPERATIONS = {'metadata-walk', 'small-file-read-write', 'git-status'}


def approved(host_role, fingerprint='sha256:abc', network_label='lab'):
    record = build_measurement(fingerprint, host_role, network_label)
    record['review']['status'] = 'approved'
    record['probes']['reachability'] = {'attempts': 20, 'successes': 20}
    record['probes']['latency_ms'] = {'p50': 1.0, 'p95': 2.0, 'max': 3.0}
    record['probes']['throughput_mib_s'] = {
        'read': {'samples': [100.0]}, 'write': {'samples': [90.0]},
    }
    record['probes']['workspace_smb']['operations'] = [
        {'name': name, 'duration_ms': 1.0, 'outcome': 'pass'}
        for name in REQUIRED_OPERATIONS
    ]
    return record


class MeasurementTests(unittest.TestCase):
    def test_builds_pending_non_configuring_record(self):
        record = build_measurement('sha256:abc', 'macbook', 'lab')
        self.assertEqual(record['smb_configuration'], 'unmodified')
        self.assertEqual(record['review']['status'], 'pending')
        self.assertIn('latency_ms', record['probes'])

    def test_accepts_complete_compatible_approved_evidence(self):
        self.assertTrue(adjustment_ready([approved('macbook'), approved('mac-mini')]))

    def test_fails_closed_for_every_compatibility_and_evidence_gap(self):
        baseline = [approved('macbook'), approved('mac-mini')]
        cases = [
            ('record_version', 2),
            ('plan_fingerprint', 'sha256:other'),
            ('fixture_version', 'representative-tree-v2'),
            ('network_label', 'other-network'),
            ('smb_configuration', 'modified'),
        ]
        for field, value in cases:
            with self.subTest(field=field):
                records = [approved('macbook'), approved('mac-mini')]
                target = records[1]
                if field == 'network_label':
                    target['environment']['network_label'] = value
                else:
                    target[field] = value
                self.assertFalse(adjustment_ready(records))
        for role in ('macbook', 'mac-mini'):
            with self.subTest(missing_role=role):
                self.assertFalse(adjustment_ready([approved(role), approved(role)]))
        malformed = [approved('macbook'), approved('mac-mini')]
        malformed[1]['environment'] = None
        self.assertFalse(adjustment_ready(malformed))
        for mutation in (
            lambda record: record['probes']['reachability'].update(successes=0),
            lambda record: record['probes']['latency_ms'].update(p95=0.5),
            lambda record: record['probes']['throughput_mib_s'].pop('write'),
            lambda record: record['probes']['throughput_mib_s']['read'].update(samples=[0.0]),
            lambda record: record['probes']['workspace_smb'].update(operations=[]),
            lambda record: record['probes']['workspace_smb']['operations'].pop(),
        ):
            records = baseline = [approved('macbook'), approved('mac-mini')]
            mutation(records[0])
            self.assertFalse(adjustment_ready(records))


if __name__ == '__main__':
    unittest.main()
