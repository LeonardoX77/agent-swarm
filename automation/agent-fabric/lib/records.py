"""Safe, local-only evidence records."""
import hashlib
import json
import os
import pwd
import tempfile
from datetime import datetime, timezone
from pathlib import Path

FORBIDDEN = (
    'password', 'secret', 'token', 'private', 'keychain', 'command', 'stderr',
    'environment', 'path',
)
ACTIVITY_FIELDS = {'agent_id', 'repository_id', 'host_id', 'operation_id', 'outcome'}
OPTIONAL_ACTIVITY_FIELDS = {'area'}


def _contains_forbidden_key(value):
    if isinstance(value, dict):
        return any(any(word in str(key).lower() for word in FORBIDDEN) or _contains_forbidden_key(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _safe(value):
    if isinstance(value, dict):
        return {key: _safe(item) for key, item in value.items() if not any(word in key.lower() for word in FORBIDDEN)}
    if isinstance(value, list):
        return [_safe(item) for item in value]
    return value


def effective_user():
    """Return the account owning the process's effective user ID."""
    return pwd.getpwuid(os.geteuid()).pw_name


def _inside(path, root):
    return path != root and root in path.parents


def _has_symlink_component(path, start=None):
    current = Path(path.anchor) if start is None else start
    parts = path.parts[1:] if start is None else path.relative_to(start).parts
    for part in parts:
        current /= part
        try:
            if current.is_symlink():
                return True
        except OSError:
            return True
    return False


def local_destination(path):
    """Accept only local per-user activity directories or test temp files."""
    try:
        candidate = Path(path)
        if not candidate.is_absolute() or '..' in candidate.parts:
            return False
        temporary = Path(tempfile.gettempdir())
        if _inside(candidate, temporary):
            return not _has_symlink_component(candidate, temporary)
        if _has_symlink_component(candidate):
            return False
        user_home = Path('/Users') / effective_user()
        approved = (
            user_home / '.local/state/agent-fabric',
            user_home / 'Library/Logs/AgentFabric',
        )
        return any(_inside(candidate, root) for root in approved)
    except (OSError, RuntimeError, TypeError, ValueError, KeyError):
        return False


def _timestamp(): return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def write_event(path, event):
    path = Path(path)
    if not local_destination(path): raise ValueError('UNSAFE_RECORD_DESTINATION')
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {'record_version': 1, 'timestamp': _timestamp(), **_safe(event)}
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(descriptor, 'a', encoding='utf-8') as stream: stream.write(json.dumps(payload, sort_keys=True) + '\n')
    return payload


def activity_event(event):
    if not isinstance(event, dict) or _contains_forbidden_key(event): raise ValueError('INVALID_ACTIVITY_EVENT')
    if set(event) - (ACTIVITY_FIELDS | OPTIONAL_ACTIVITY_FIELDS) or not ACTIVITY_FIELDS.issubset(event): raise ValueError('INVALID_ACTIVITY_EVENT')
    if not all(isinstance(event[field], str) and event[field] for field in ACTIVITY_FIELDS): raise ValueError('INVALID_ACTIVITY_EVENT')
    if 'area' in event and (not isinstance(event['area'], str) or not event['area']): raise ValueError('INVALID_ACTIVITY_EVENT')
    return {'agent_id_sha256': hashlib.sha256(event['agent_id'].encode()).hexdigest(), 'repository_id_sha256': hashlib.sha256(event['repository_id'].encode()).hexdigest(), 'host_id_sha256': hashlib.sha256(event['host_id'].encode()).hexdigest(), 'operation_id': event['operation_id'], **({'area': event['area']} if 'area' in event else {}), 'outcome': event['outcome']}


def fabric_activity_event(request, status, host_role, duration_seconds, diagnostic_code):
    """Return an observability-only event; it grants no execution authority."""
    if host_role not in ('macbook', 'mac-mini') or not isinstance(duration_seconds, (int, float)) or duration_seconds < 0 or not isinstance(diagnostic_code, str) or not diagnostic_code:
        raise ValueError('INVALID_FABRIC_ACTIVITY_EVENT')
    return {
        'event_type': 'fabric_activity',
        'request_id_sha256': hashlib.sha256(request['request_id'].encode()).hexdigest(),
        'workspace': request['workspace'],
        'host_role': host_role,
        'status': status,
        'duration_seconds': duration_seconds,
        'diagnostic_code': diagnostic_code,
    }
