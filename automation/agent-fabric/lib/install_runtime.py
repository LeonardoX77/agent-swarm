"""Install Agent Fabric runtime files into the current user's HOME only."""
import json
import os
import pwd
import shutil
import stat
from pathlib import Path

from ssh_policy import authorized_keys_line

HOSTS = {'macbook': 'macbook', 'mac-mini': 'mac-mini'}
ROLE_USERS = {'macbook': 'leo', 'mac-mini': 'leo'}
RUNTIME_RELATIVE = Path('.local/agent-fabric')
FILES = (
    ('bin/fabric-runner', 'bin/fabric-runner'),
    ('bin/fabric-dispatch', 'bin/fabric-dispatch'),
    ('bin/fabric-host-preflight', 'bin/fabric-host-preflight'),
    ('bin/fabric-activity', 'bin/fabric-activity'),
    ('lib/environment.py', 'lib/environment.py'),
    ('lib/process.py', 'lib/process.py'),
    ('lib/records.py', 'lib/records.py'),
    ('lib/request.py', 'lib/request.py'),
    ('lib/host_config.py', 'lib/host_config.py'),
    ('lib/ssh_policy.py', 'lib/ssh_policy.py'),
)
MANIFEST = '.fabric-install-runtime.json'


def _role(role):
    if role not in HOSTS:
        raise ValueError('INVALID_HOST_ROLE')
    return role


def effective_user():
    """Return the account owning the process's effective user ID."""
    return pwd.getpwuid(os.geteuid()).pw_name


def _paths(home):
    root = Path(home).expanduser() / RUNTIME_RELATIVE
    return root, root / 'bin/fabric-runner', root / 'config/host.json'


def _public_key(path):
    try:
        text = Path(path).read_text(encoding='utf-8')
    except OSError as error:
        raise ValueError('PEER_PUBLIC_KEY_UNAVAILABLE') from error
    if not text.endswith('\n') or '\n' in text[:-1]:
        raise ValueError('INVALID_PUBLIC_KEY')
    return text[:-1]


def plan(source_root, home, role, peer_public_key):
    """Return an installation plan; this function never writes."""
    role = _role(role)
    source = Path(source_root)
    runtime, runner, config = _paths(home)
    public_key = _public_key(peer_public_key)
    return {
        'role': role,
        'runtime_root': str(runtime),
        'host_config': str(config),
        'files': [str(runtime / destination) for _, destination in FILES] + [str(config)],
        'authorized_keys_line': authorized_keys_line(str(runner), str(config), public_key),
    }


def apply(source_root, home, role, peer_public_key):
    """Copy only runtime files and its host configuration beneath HOME."""
    role = _role(role)
    if effective_user() != ROLE_USERS[role]:
        raise ValueError('UNEXPECTED_USER')
    details = plan(source_root, home, role, peer_public_key)
    source = Path(source_root)
    runtime = Path(details['runtime_root'])
    installed = []
    for origin, destination in FILES:
        target = runtime / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / origin, target)
        if target.parent.name == 'bin':
            target.chmod(target.stat().st_mode | stat.S_IXUSR)
        installed.append(destination)
    config = Path(details['host_config'])
    config.parent.mkdir(parents=True, exist_ok=True)
    repository = source if (source / 'config').is_dir() else source.parents[1]
    shutil.copy2(repository / 'config' / HOSTS[role] / 'host.json', config)
    installed.append('config/host.json')
    (runtime / MANIFEST).write_text(json.dumps({'files': installed}, sort_keys=True) + '\n', encoding='utf-8')
    return details


def revert(home):
    """Remove only files recorded by this helper, leaving unrelated files intact."""
    runtime, _, _ = _paths(home)
    manifest = runtime / MANIFEST
    if not manifest.is_file():
        return {'reverted': False}
    try:
        files = json.loads(manifest.read_text(encoding='utf-8'))['files']
    except (OSError, ValueError, KeyError, TypeError):
        raise ValueError('INVALID_RUNTIME_MANIFEST') from None
    if not isinstance(files, list) or any(not isinstance(item, str) or Path(item).is_absolute() or '..' in Path(item).parts for item in files):
        raise ValueError('INVALID_RUNTIME_MANIFEST')
    for relative in files:
        target = runtime / relative
        if target.is_file() or target.is_symlink():
            target.unlink()
    manifest.unlink()
    for directory in sorted((path for path in runtime.rglob('*') if path.is_dir()), key=lambda path: len(path.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass
    try:
        runtime.rmdir()
    except OSError:
        pass
    return {'reverted': True}
