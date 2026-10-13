"""Private durable admission ledger for one host-local Herdr task attempt."""
import errno
import fcntl
import hashlib
import json
import os
import stat
import tempfile
import threading
import uuid
from pathlib import Path

MAX_RECORD = 65536
PHASES = {
    'reserved': {'create_intent'}, 'create_intent': {'created', 'unknown'},
    'created': {'start_intent'}, 'start_intent': {'started', 'unknown'},
    'started': {'submit_intent'}, 'submit_intent': {'submitted', 'unknown', 'recover_intent', 'result'},
    'submitted': {'result', 'unknown', 'recover_intent'},
    'unknown': {'recover_intent', 'result'}, 'recover_intent': {'result', 'unknown'},
    'result': {'cleanup_intent', 'closed'}, 'cleanup_intent': {'closed'}, 'closed': set(),
}
_BINDINGS = {'session_id', 'pane_id', 'tab_id', 'agent_id'}
_LOCKS, _LOCKS_GUARD = {}, threading.Lock()

class LedgerError(ValueError): pass
class LedgerConflict(LedgerError): pass
class LedgerCorrupt(LedgerError): pass
class UnsafeLedgerRoot(LedgerError): pass


def _uuid(value):
    try: value = str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError): raise LedgerError('INVALID_TASK_ID')
    return value


def _safe_components(path):
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            # /var is macOS's fixed system alias; all caller-controlled links fail.
            if current.is_symlink() and current != Path('/var'): return False
        except OSError: return False
    return True


def _private(path, mode):
    info = os.stat(path, follow_symlinks=False)
    return info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == mode


def _root(value):
    path = Path.home() / '.local/state/agent-fabric/herdr' if value is None else Path(value)
    if not path.is_absolute() or '..' in path.parts or path.parts[1:2] == ('Volumes',) or path.is_symlink() or not _safe_components(path): raise UnsafeLedgerRoot('UNSAFE_LEDGER_ROOT')
    path = path.resolve(strict=False)  # permits only the fixed macOS /var alias.
    temporary, home = Path(tempfile.gettempdir()).resolve(), Path.home().resolve()
    if not (path.is_relative_to(temporary) or path.is_relative_to(home / '.local/state')) or not _safe_components(path): raise UnsafeLedgerRoot('UNSAFE_LEDGER_ROOT')
    return path


def _payload(value):
    allowed = {'user_prompt', 'planned_session_id', 'planned_agent', 'cwd'}
    required = allowed - {'cwd'}
    if not isinstance(value, dict) or not required.issubset(value) or set(value) - allowed or any(not isinstance(value[k], str) or not value[k] for k in value): raise LedgerError('INVALID_PAYLOAD')
    data = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    if len(data) > MAX_RECORD // 2: raise LedgerError('PAYLOAD_TOO_LARGE')
    return json.loads(data), hashlib.sha256(data).hexdigest()


def _bindings(value):
    if value is None: return {}
    if not isinstance(value, dict) or set(value) - _BINDINGS or any(not isinstance(k, str) or not isinstance(v, str) or not v for k, v in value.items()): raise LedgerConflict('INVALID_BINDINGS')
    return value


class Ledger:
    def __init__(self, root=None):
        self.root = _root(root); self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not _safe_components(self.root) or not _private(self.root, 0o700): raise UnsafeLedgerRoot('UNSAFE_LEDGER_ROOT')

    def _path(self, task): return self.root / (_uuid(task) + '.json')
    def _rootfd(self):
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        info = os.fstat(fd)
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
            os.close(fd); raise UnsafeLedgerRoot('UNSAFE_LEDGER_ROOT')
        return fd
    def _lock(self, task):
        task = _uuid(task); key = (str(self.root), task)
        with _LOCKS_GUARD: mutex = _LOCKS.setdefault(key, threading.Lock())
        mutex.acquire(); rootfd = None
        try:
            rootfd = self._rootfd()
            fd = os.open('.' + task + '.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=rootfd)
            info = os.fstat(fd)
            os.close(rootfd); rootfd = None
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600:
                os.close(fd); raise LedgerCorrupt('UNSAFE_LOCK')
            fcntl.flock(fd, fcntl.LOCK_EX); return fd, mutex
        except OSError as error:
            if rootfd is not None: os.close(rootfd)
            mutex.release(); raise LedgerCorrupt('UNSAFE_LOCK') from error
        except Exception:
            if rootfd is not None: os.close(rootfd)
            mutex.release(); raise
    def _unlock(self, lock):
        fd, mutex = lock; fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd); mutex.release()

    def _read(self, task):
        name, rootfd = _uuid(task) + '.json', self._rootfd()
        try:
            try: fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=rootfd)
            except OSError as error:
                if error.errno == errno.ENOENT: return None
                raise LedgerCorrupt('UNSAFE_LEDGER_FILE') from error
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600: raise LedgerCorrupt('UNSAFE_LEDGER_FILE')
                chunks, size = [], 0
                while True:
                    chunk = os.read(fd, min(65536, MAX_RECORD + 1 - size))
                    if not chunk: break
                    chunks.append(chunk); size += len(chunk)
                    if size > MAX_RECORD: raise LedgerCorrupt('CORRUPT_LEDGER')
                data = b''.join(chunks)
            finally: os.close(fd)
        finally: os.close(rootfd)
        try:
            if not data: raise ValueError
            record = json.loads(data)
        except (ValueError, json.JSONDecodeError): raise LedgerCorrupt('CORRUPT_LEDGER')
        required = {'task_id', 'payload', 'payload_hash', 'phase', 'bindings'}
        if not isinstance(record, dict) or set(record) != required or record['task_id'] != _uuid(task) or record['phase'] not in PHASES: raise LedgerCorrupt('CORRUPT_LEDGER')
        payload, digest = _payload(record['payload']); bindings = _bindings(record['bindings'])
        if payload != record['payload'] or digest != record['payload_hash'] or bindings != record['bindings']: raise LedgerCorrupt('CORRUPT_LEDGER')
        return record

    def _write(self, task, record):
        data = json.dumps(record, sort_keys=True, separators=(',', ':')).encode()
        if len(data) > MAX_RECORD: raise LedgerError('RECORD_TOO_LARGE')
        fd, name = tempfile.mkstemp(prefix='.', dir=self.root)
        try:
            os.fchmod(fd, 0o600); offset = 0
            while offset < len(data): offset += os.write(fd, data[offset:])
            os.fsync(fd); os.close(fd); fd = None
            directory = self._rootfd()
            try:
                os.replace(Path(name).name, _uuid(task) + '.json', src_dir_fd=directory, dst_dir_fd=directory)
                os.fsync(directory)
            finally: os.close(directory)
        finally:
            if fd is not None: os.close(fd)
            try: os.unlink(name)
            except FileNotFoundError: pass

    def reserve(self, task_id, payload):
        task_id = _uuid(task_id); payload, digest = _payload(payload); lock = self._lock(task_id)
        try:
            old = self._read(task_id)
            if old:
                if old['payload'] != payload or old['payload_hash'] != digest: raise LedgerConflict('IMMUTABLE_PAYLOAD')
                return old
            record = {'task_id': task_id, 'payload': payload, 'payload_hash': digest, 'phase': 'reserved', 'bindings': {}}
            self._write(task_id, record); return record
        finally: self._unlock(lock)

    def load(self, task_id):
        lock = self._lock(task_id)
        try:
            record = self._read(task_id)
            if record is None: raise LedgerError('TASK_NOT_RESERVED')
            return record
        finally: self._unlock(lock)

    def update(self, task_id, phase, expected_phase, bindings=None):
        if phase not in PHASES or expected_phase not in PHASES: raise LedgerConflict('INVALID_PHASE')
        task_id = _uuid(task_id); lock = self._lock(task_id)
        try:
            record = self._read(task_id)
            if record is None: raise LedgerError('TASK_NOT_RESERVED')
            if record['phase'] != expected_phase or phase not in PHASES[expected_phase]: raise LedgerConflict('INVALID_TRANSITION')
            additions = _bindings(bindings)
            if any(key in record['bindings'] and record['bindings'][key] != value for key, value in additions.items()): raise LedgerConflict('IMMUTABLE_BINDING')
            record['bindings'] = {**record['bindings'], **additions}; record['phase'] = phase
            self._write(task_id, record); return record
        finally: self._unlock(lock)
