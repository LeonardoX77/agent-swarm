"""Safe, local-only evidence records."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

FORBIDDEN = (
    'password', 'secret', 'token', 'private', 'keychain', 'command', 'stderr',
    'environment', 'path',
)
UNSAFE_DESTINATION_PREFIXES = ('/Users/', '/Volumes/', '/net/', '/mnt/', '/media/')
ACTIVITY_FIELDS = {'agent_id', 'repository_id', 'host_id', 'operation_id', 'outcome'}
OPTIONAL_ACTIVITY_FIELDS = {'area'}


def _contains_forbidden_key(value):
    if isinstance(value, dict):
        return any(
            any(word in str(key).lower() for word in FORBIDDEN)
            or _contains_forbidden_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _safe(value):
    if isinstance(value, dict):
        return {
            key: _safe(item) for key, item in value.items()
            if not any(word in key.lower() for word in FORBIDDEN)
        }
    if isinstance(value, list):
        return [_safe(item) for item in value]
    return value


def local_destination(path):
    """Return whether a record destination is local and safely resolvable."""
    try:
        candidate = Path(path)
        if not candidate.is_absolute():
            return False
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError, TypeError, ValueError):
        return False
    return not any(
        str(location).startswith(UNSAFE_DESTINATION_PREFIXES)
        for location in (candidate, resolved)
    )


def _timestamp():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def write_event(path, event):
    path = Path(path)
    if not local_destination(path):
        raise ValueError('UNSAFE_RECORD_DESTINATION')
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {'record_version': 1, 'timestamp': _timestamp(), **_safe(event)}
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(descriptor, 'a', encoding='utf-8') as stream:
        stream.write(json.dumps(payload, sort_keys=True) + '\n')
    return payload


def activity_event(event):
    if not isinstance(event, dict) or _contains_forbidden_key(event):
        raise ValueError('INVALID_ACTIVITY_EVENT')
    if set(event) - (ACTIVITY_FIELDS | OPTIONAL_ACTIVITY_FIELDS):
        raise ValueError('INVALID_ACTIVITY_EVENT')
    if not ACTIVITY_FIELDS.issubset(event):
        raise ValueError('INVALID_ACTIVITY_EVENT')
    if not all(isinstance(event[field], str) and event[field] for field in ACTIVITY_FIELDS):
        raise ValueError('INVALID_ACTIVITY_EVENT')
    if 'area' in event and (not isinstance(event['area'], str) or not event['area']):
        raise ValueError('INVALID_ACTIVITY_EVENT')
    return {
        'agent_id_sha256': hashlib.sha256(event['agent_id'].encode()).hexdigest(),
        'repository_id_sha256': hashlib.sha256(event['repository_id'].encode()).hexdigest(),
        'host_id_sha256': hashlib.sha256(event['host_id'].encode()).hexdigest(),
        'operation_id': event['operation_id'],
        **({'area': event['area']} if 'area' in event else {}),
        'outcome': event['outcome'],
    }
