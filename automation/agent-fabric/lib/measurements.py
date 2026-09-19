"""Synthetic, non-configuring baseline evidence."""
from datetime import datetime, timezone

REQUIRED_OPERATIONS = {'metadata-walk', 'small-file-read-write', 'git-status'}
REQUIRED_ROLES = {'macbook', 'mac-mini'}


def build_measurement(fingerprint, host_role, network_label):
    return {
        'record_version': 1,
        'recorded_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'plan_fingerprint': fingerprint,
        'host_role': host_role,
        'environment': {'network_label': network_label},
        'fixture_version': 'representative-tree-v1',
        'probes': {
            'reachability': {'attempts': 0, 'successes': 0},
            'latency_ms': {'p50': None, 'p95': None, 'max': None},
            'throughput_mib_s': {'read': {'samples': []}, 'write': {'samples': []}},
            'workspace_smb': {'fixture': 'representative-tree-v1', 'operations': []},
        },
        'smb_configuration': 'unmodified',
        'review': {'status': 'pending', 'reviewed_at': None, 'decision': None},
    }


def _mapping(value):
    return value if isinstance(value, dict) else None


def _positive_samples(samples):
    return isinstance(samples, list) and bool(samples) and all(isinstance(sample, (int, float)) and not isinstance(sample, bool) and sample > 0 for sample in samples)


def _valid_probes(record):
    probes = _mapping(record.get('probes'))
    if probes is None:
        return False
    reachability = _mapping(probes.get('reachability'))
    latency = _mapping(probes.get('latency_ms'))
    throughput = _mapping(probes.get('throughput_mib_s'))
    workspace = _mapping(probes.get('workspace_smb'))
    if None in (reachability, latency, throughput, workspace):
        return False
    attempts, successes = reachability.get('attempts'), reachability.get('successes')
    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts <= 0 or not isinstance(successes, int) or isinstance(successes, bool) or not 0 < successes <= attempts:
        return False
    values = [latency.get(key) for key in ('p50', 'p95', 'max')]
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 for value in values) or not values[0] <= values[1] <= values[2]:
        return False
    if not all(
        _positive_samples((_mapping(throughput.get(direction)) or {}).get('samples'))
        for direction in ('read', 'write')
    ):
        return False
    if workspace.get('fixture') != record.get('fixture_version'):
        return False
    operations = workspace.get('operations')
    if not isinstance(operations, list):
        return False
    observed = {operation.get('name') for operation in operations if isinstance(operation, dict) and operation.get('outcome') == 'pass' and isinstance(operation.get('duration_ms'), (int, float)) and operation['duration_ms'] >= 0}
    return REQUIRED_OPERATIONS.issubset(observed)


def adjustment_ready(records):
    if not isinstance(records, list) or len(records) != 2 or not all(isinstance(record, dict) for record in records):
        return False
    roles = {record.get('host_role') for record in records}
    environments = [_mapping(record.get('environment')) for record in records]
    reviews = [_mapping(record.get('review')) for record in records]
    if roles != REQUIRED_ROLES or any(environment is None for environment in environments) or any(review is None for review in reviews):
        return False
    fingerprints = {record.get('plan_fingerprint') for record in records}
    fixtures = {record.get('fixture_version') for record in records}
    labels = {environment.get('network_label') for environment in environments}
    if any(len(values) != 1 or None in values for values in (fingerprints, fixtures, labels)):
        return False
    return all(
        record.get('record_version') == 1
        and review.get('status') == 'approved'
        and record.get('smb_configuration') == 'unmodified'
        and _valid_probes(record)
        for record, review in zip(records, reviews)
    )
