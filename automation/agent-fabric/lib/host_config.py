"""Strict local-only host configuration validation."""
from pathlib import Path

REQUIRED = {'version', 'role', 'expected_user', 'max_timeout_seconds', 'workspace_roots', 'ssh_aliases'}
OPTIONAL = {'activity_record'}
SECRET_WORDS = ('password', 'secret', 'token', 'credential', 'key', 'private')


def load_config(value):
    if not isinstance(value, dict) or set(value) - (REQUIRED | OPTIONAL) or not REQUIRED.issubset(value):
        raise ValueError('INVALID_HOST_CONFIG')
    if any(any(word in str(key).lower() for word in SECRET_WORDS) for key in value):
        raise ValueError('INVALID_HOST_CONFIG')
    if value['version'] != 1 or value['role'] not in ('macbook', 'mac-mini'):
        raise ValueError('INVALID_HOST_CONFIG')
    if not isinstance(value['expected_user'], str) or not value['expected_user']:
        raise ValueError('INVALID_HOST_CONFIG')
    maximum = value['max_timeout_seconds']
    if isinstance(maximum, bool) or not isinstance(maximum, int) or not 1 <= maximum <= 3600:
        raise ValueError('INVALID_HOST_CONFIG')
    roots = value['workspace_roots']
    aliases = value['ssh_aliases']
    if not isinstance(roots, dict) or not roots or not isinstance(aliases, dict):
        raise ValueError('INVALID_HOST_CONFIG')
    for workspace, root in roots.items():
        if not isinstance(workspace, str) or not workspace or not isinstance(root, str) or not Path(root).is_absolute():
            raise ValueError('INVALID_HOST_CONFIG')
    for host, alias in aliases.items():
        if host not in ('macbook', 'mac-mini') or not isinstance(alias, str) or not alias or any(char.isspace() for char in alias):
            raise ValueError('INVALID_HOST_CONFIG')
    if 'activity_record' in value and (not isinstance(value['activity_record'], str) or not Path(value['activity_record']).is_absolute()):
        raise ValueError('INVALID_HOST_CONFIG')
    return value
