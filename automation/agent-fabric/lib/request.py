"""Fail-closed validation for the Agent Fabric v1 task transport."""
import re
import uuid

FIELDS = {'version', 'request_id', 'workspace', 'relative_path', 'prompt', 'runtime', 'initiator', 'timeout_seconds'}
SECRET_WORDS = ('password', 'secret', 'token', 'credential', 'key', 'private')
WORKSPACE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')


def validate_request(value):
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ValueError('INVALID_TASK_REQUEST')
    if any(word in key.lower() for key in value for word in SECRET_WORDS):
        raise ValueError('INVALID_TASK_REQUEST')
    if value['version'] != 1:
        raise ValueError('INVALID_TASK_REQUEST')
    try:
        if str(uuid.UUID(value['request_id'])) != value['request_id'].lower():
            raise ValueError
    except (ValueError, AttributeError, TypeError):
        raise ValueError('INVALID_TASK_REQUEST') from None
    if not isinstance(value['workspace'], str) or not WORKSPACE.fullmatch(value['workspace']):
        raise ValueError('INVALID_TASK_REQUEST')
    path = value['relative_path']
    if not isinstance(path, str) or not path or path.startswith('/') or path.startswith('./'):
        raise ValueError('INVALID_TASK_REQUEST')
    if path != '.' and any(part in ('', '.', '..') for part in path.split('/')):
        raise ValueError('INVALID_TASK_REQUEST')
    if not isinstance(value['prompt'], str) or not value['prompt'].strip() or len(value['prompt'].encode('utf-8')) > 16384:
        raise ValueError('INVALID_TASK_REQUEST')
    if value['runtime'] not in ('pi', 'opencode', 'claude'):
        raise ValueError('INVALID_TASK_REQUEST')
    if value['initiator'] not in ('macbook', 'mac-mini'):
        raise ValueError('INVALID_TASK_REQUEST')
    if isinstance(value['timeout_seconds'], bool) or not isinstance(value['timeout_seconds'], int) or value['timeout_seconds'] <= 0:
        raise ValueError('INVALID_TASK_REQUEST')
    return value
