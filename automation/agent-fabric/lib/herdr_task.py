"""Host-local, at-most-one-attempt controller for owned Pi agents in Herdr."""
import json
import os
import shutil
from datetime import datetime, timezone
import stat
import subprocess
import uuid
from pathlib import Path

from herdr_ledger import Ledger, LedgerConflict, LedgerError
from pi_session_result import SessionError, parse_session_result

_FIELDS = {'task_id', 'origin_host', 'project', 'goal', 'acceptance', 'mode'}
_HOST_ROOTS = {'MacMiniLeo': Path('/Volumes/agent-projects'), 'MacBookLeo': Path('/Users/leo/projects')}


class TaskError(ValueError):
    pass


def _uuid(value):
    try:
        parsed = str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError) as error:
        raise TaskError('INVALID_TASK_ID') from error
    if parsed != value:
        raise TaskError('INVALID_TASK_ID')
    return parsed


def _safe_absolute(value, *, exists=True):
    path = Path(value)
    if not path.is_absolute() or path == Path('/') or '..' in path.parts:
        raise TaskError('UNSAFE_PATH')
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink() and current != Path('/var'):
            raise TaskError('UNSAFE_PATH')
    try:
        return path.resolve(strict=exists)
    except OSError as error:
        raise TaskError('UNSAFE_PATH') from error


def _private_directory(path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = os.stat(path, follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise TaskError('UNSAFE_STATE_DIR')


def _envelope(value):
    if not isinstance(value, dict) or set(value) != _FIELDS:
        raise TaskError('INVALID_ENVELOPE')
    task = _uuid(value['task_id'])
    if any(not isinstance(value[key], str) or not value[key] or len(value[key].encode()) > 16384 for key in _FIELDS - {'task_id'}):
        raise TaskError('INVALID_ENVELOPE')
    if value['mode'] != 'executor':
        raise TaskError('UNSUPPORTED_MODE')
    project = value['project']
    if project.startswith('/') or any(part in ('', '.', '..') for part in project.split('/')):
        raise TaskError('INVALID_PROJECT')
    return {**value, 'task_id': task}


class Controller:
    def __init__(self, state_dir=None, *, herdr=None, project_root=None, hostname=None, gui_cwd='/Users/leo/tmp', timeout=30, run=None):
        self.hostname = hostname or os.uname().nodename
        self.timeout = timeout
        self.gui_cwd = _safe_absolute(gui_cwd)
        if not self.gui_cwd.is_dir():
            raise TaskError('UNSAFE_GUI_CWD')
        if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 300:
            raise TaskError('INVALID_TIMEOUT')
        self.state = _safe_absolute(state_dir or (Path.home() / '.local/state/agent-fabric/herdr-task'), exists=False)
        _private_directory(self.state)
        self.sessions = self.state / 'sessions'; _private_directory(self.sessions)
        self.ledger = Ledger(self.state / 'ledger')
        self.explicit_project = project_root is not None
        self.project = self._project(project_root)
        binary = herdr or shutil.which('herdr')
        if not binary:
            raise TaskError('MISSING_HERDR')
        candidate = Path(binary)
        if not candidate.is_absolute():
            raise TaskError('MISSING_HERDR')
        try:
            self.herdr = candidate.resolve(strict=True)
        except OSError as error:
            raise TaskError('MISSING_HERDR') from error
        if not self.herdr.is_file() or not os.access(self.herdr, os.X_OK):
            raise TaskError('MISSING_HERDR')
        self.run = run or subprocess.run
        self.last_error = None

    def _project(self, explicit):
        if explicit is not None:
            path = _safe_absolute(explicit)
            if not path.is_dir():
                raise TaskError('INVALID_PROJECT')
            return path
        root = next((root for prefix, root in _HOST_ROOTS.items() if self.hostname.startswith(prefix)), None)
        if root is None:
            raise TaskError('UNSUPPORTED_HOST')
        return _safe_absolute(root)

    def _call(self, argv):
        try:
            completed = self.run(argv, input=None, text=True, capture_output=True, timeout=self.timeout, shell=False, env=None)
        except (OSError, subprocess.TimeoutExpired) as error:
            self.last_error = {'returncode': getattr(error, 'returncode', None), 'stderr': str(getattr(error, 'stderr', '') or '')[:300]}
            return None
        if completed.returncode != 0:
            self.last_error = {'returncode': completed.returncode, 'stderr': str(completed.stderr or '')[:300]}
            for raw in (completed.stdout, completed.stderr):
                try:
                    value = json.loads(raw)
                except (TypeError, json.JSONDecodeError):
                    continue
                error = value.get('error') if isinstance(value, dict) else None
                if isinstance(error, dict) and isinstance(error.get('code'), str):
                    return value
            return None
        try:
            value = json.loads(completed.stdout)
        except (TypeError, json.JSONDecodeError):
            self.last_error = {'returncode': completed.returncode, 'stderr': str(completed.stderr or '')[:300]}
            return None
        return value if isinstance(value, dict) else None

    @staticmethod
    def _result(value):
        result = value.get('result') if isinstance(value, dict) and 'error' not in value else None
        return result if isinstance(result, dict) else None

    def _session_path(self, task):
        return self.sessions / task / 'session.jsonl'

    def _create_session(self, task):
        root = self.sessions / task
        _private_directory(root)
        path = root / 'session.jsonl'
        cwd = self.gui_cwd
        header = {'type': 'session', 'version': 3, 'id': task, 'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), 'cwd': str(cwd)}
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError as error:
            raise TaskError('SESSION_EXISTS') from error
        try:
            os.write(fd, (json.dumps(header, separators=(',', ':')) + '\n').encode('utf-8'))
            os.fsync(fd)
        finally:
            os.close(fd)
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return path

    def _payload(self, envelope):
        prompt = json.dumps(envelope, sort_keys=True, separators=(',', ':'))
        return {'user_prompt': prompt, 'planned_session_id': envelope['task_id'], 'planned_agent': 'p' + envelope['task_id'].replace('-', '')[:31], 'cwd': str(self.gui_cwd)}

    def _header_owned(self, task, payload):
        path = self._session_path(task)
        try:
            parse_session_result(path, self.sessions / task, payload['planned_session_id'], payload['user_prompt'])
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                header = json.loads(os.read(fd, 65536).splitlines()[0])
            finally:
                os.close(fd)
        except SessionError:
            raise
        except (OSError, IndexError, json.JSONDecodeError):
            return False
        return (isinstance(header, dict) and header.get('type') == 'session' and header.get('version') == 3
                and header.get('id') == payload['planned_session_id'] and header.get('cwd') == payload['cwd']
                and isinstance(header.get('timestamp'), str) and header['timestamp'])

    def _identity(self, record, value):
        agent = self._result(value)
        agent = agent.get('agent') if agent else None
        bind, payload = record['bindings'], record['payload']
        if not self._header_owned(record['task_id'], payload):
            return None
        if not isinstance(agent, dict) or agent.get('agent') != 'pi' or agent.get('name') != payload['planned_agent']:
            return None
        if agent.get('pane_id') != bind.get('pane_id') or agent.get('tab_id') != bind.get('tab_id'):
            return None
        session = agent.get('agent_session')
        required_session = {'agent': 'pi', 'kind': 'path', 'source': 'herdr:pi', 'value': str(self._session_path(record['task_id']))}
        if not isinstance(session, dict) or any(session.get(key) != expected for key, expected in required_session.items()):
            return None
        # Live Herdr output has no separate agent id. Pane id is the stable selector.
        agent_id = agent.get('pane_id')
        if not isinstance(agent_id, str) or not agent_id or ('agent_id' in bind and bind['agent_id'] != agent_id):
            return None
        if agent.get('agent_status') not in ('idle', 'working', 'blocked', 'done', 'unknown'):
            return None
        return agent_id, agent

    def _session_error(self, error):
        self.last_error = {'session_error': f'{type(error).__name__}:{error}'}

    def _unknown(self, task, expected):
        try:
            self.ledger.update(task, 'unknown', expected)
        except LedgerConflict:
            pass
        return self._report(self.ledger.load(task))

    def _report(self, record):
        phase = record['phase']
        if phase in ('result', 'cleanup_intent', 'closed'):
            try:
                parsed = parse_session_result(self._session_path(record['task_id']), self.sessions / record['task_id'], record['payload']['planned_session_id'], record['payload']['user_prompt'])
            except SessionError as error:
                self._session_error(error)
                parsed = None
            if parsed and parsed.status == 'result':
                status = 'done' if phase == 'result' else phase
                return {'task_id': record['task_id'], 'status': status, 'resulttext': parsed.text, 'userentry': parsed.user_entry, 'assistantentry': parsed.assistant_entry, 'resubmit': False}
            report = {'task_id': record['task_id'], 'status': 'unknown', 'diagnostic_code': 'UNREADABLE_RESULT_SESSION', 'resubmit': False}
        else:
            report = {'task_id': record['task_id'], 'status': phase, 'resubmit': False}
        if report['status'] == 'unknown' and self.last_error is not None:
            report['last_error'] = self.last_error
        return report

    def submit(self, raw):
        self.last_error = None
        envelope = _envelope(raw)
        # project is always a safe relative path below the selected catalog root.
        project = _safe_absolute(self.project / envelope['project'])
        try:
            project.relative_to(self.project)
        except ValueError as error:
            raise TaskError('PROJECT_MISMATCH') from error
        if project == self.project or not project.is_dir():
            raise TaskError('PROJECT_MISMATCH')
        payload = self._payload(envelope)
        try:
            record = self.ledger.reserve(envelope['task_id'], payload)
        except LedgerConflict as error:
            raise TaskError(str(error)) from error
        if record['phase'] != 'reserved':
            return self._report(record)
        try:
            record = self.ledger.update(envelope['task_id'], 'create_intent', 'reserved')
        except LedgerConflict:
            return self._report(self.ledger.load(envelope['task_id']))
        try:
            session = self._create_session(envelope['task_id'])
        except TaskError:
            return self._unknown(envelope['task_id'], 'create_intent')
        created = self._result(self._call([str(self.herdr), 'tab', 'create', '--cwd', str(self.gui_cwd), '--no-focus']))
        try:
            tab, pane = created['tab']['tab_id'], created['root_pane']['pane_id']
            if not isinstance(tab, str) or not tab or not isinstance(pane, str) or not pane:
                raise ValueError
        except (TypeError, KeyError, ValueError):
            return self._unknown(envelope['task_id'], 'create_intent')
        record = self.ledger.update(envelope['task_id'], 'created', 'create_intent', {'tab_id': tab, 'pane_id': pane, 'session_id': envelope['task_id']})
        record = self.ledger.update(envelope['task_id'], 'start_intent', 'created')
        started = self._result(self._call([str(self.herdr), 'agent', 'start', payload['planned_agent'], '--kind', 'pi', '--pane', pane, '--timeout', str(self.timeout * 1000), '--', '--session', str(session)]))
        candidate = {'result': started} if started else None
        owned = self._identity(record, candidate) if candidate else None
        if not owned:
            return self._unknown(envelope['task_id'], 'start_intent')
        identity = self._call([str(self.herdr), 'agent', 'get', owned[0]])
        owned = self._identity(record, identity)
        if not owned:
            return self._unknown(envelope['task_id'], 'start_intent')
        record = self.ledger.update(envelope['task_id'], 'started', 'start_intent', {'agent_id': owned[0]})
        record = self.ledger.update(envelope['task_id'], 'submit_intent', 'started')
        accepted = self._result(self._call([str(self.herdr), 'agent', 'prompt', owned[0], payload['user_prompt']]))
        if not isinstance(accepted, dict) or accepted.get('type') != 'agent_prompted':
            return self._unknown(envelope['task_id'], 'submit_intent')
        if 'agent' in accepted and not self._identity(record, {'result': {'agent': accepted['agent']}}):
            return self._unknown(envelope['task_id'], 'submit_intent')
        return self._report(self.ledger.update(envelope['task_id'], 'submitted', 'submit_intent'))

    def recover(self, task):
        task = _uuid(task); record = self.ledger.load(task)
        if record['phase'] == 'result' or record['phase'] == 'closed':
            return self._report(record)
        if record['phase'] not in ('submitted', 'submit_intent', 'unknown', 'recover_intent') or not set(('tab_id', 'pane_id', 'agent_id', 'session_id')).issubset(record['bindings']):
            return self._report(record)
        if record['phase'] != 'recover_intent':
            try:
                record = self.ledger.update(task, 'recover_intent', record['phase'])
            except LedgerConflict:
                return self._report(self.ledger.load(task))
        try:
            identity = self._identity(record, self._call([str(self.herdr), 'agent', 'get', record['bindings']['agent_id']]))
            if not identity:
                return self._unknown(task, 'recover_intent')
            parsed = parse_session_result(self._session_path(task), self.sessions / task, record['payload']['planned_session_id'], record['payload']['user_prompt'])
        except SessionError as error:
            self._session_error(error)
            return self._unknown(task, 'recover_intent')
        if parsed.status != 'result' or identity[1]['agent_status'] not in ('idle', 'done'):
            return {'task_id': task, 'status': 'pending', 'resubmit': False}
        try:
            return self._report(self.ledger.update(task, 'result', 'recover_intent'))
        except LedgerConflict:
            return self._report(self.ledger.load(task))

    def close(self, task):
        task = _uuid(task); record = self.ledger.load(task)
        if record['phase'] == 'closed':
            return self._report(record)
        if record['phase'] == 'cleanup_intent':
            value = self._call([str(self.herdr), 'tab', 'get', record['bindings'].get('tab_id', '')])
            error = value.get('error', {}) if value else {}
            if isinstance(error, dict) and error.get('code') == 'tab_not_found':
                return self._report(self.ledger.update(task, 'closed', 'cleanup_intent'))
            if self._result(value) is not None:
                return self._report(record)
            return {'task_id': task, 'status': 'unknown', 'resubmit': False}
        if record['phase'] != 'result':
            return {'task_id': task, 'status': 'refused', 'resubmit': False}
        identity = self._identity(record, self._call([str(self.herdr), 'agent', 'get', record['bindings'].get('agent_id', '')]))
        if not identity or identity[1]['agent_status'] not in ('idle', 'done'):
            return {'task_id': task, 'status': 'refused', 'resubmit': False}
        try:
            parsed = parse_session_result(self._session_path(task), self.sessions / task, record['payload']['planned_session_id'], record['payload']['user_prompt'])
        except SessionError:
            return {'task_id': task, 'status': 'refused', 'resubmit': False}
        if parsed.status != 'result':
            return {'task_id': task, 'status': 'refused', 'resubmit': False}
        record = self.ledger.update(task, 'cleanup_intent', 'result')
        if self._result(self._call([str(self.herdr), 'tab', 'close', record['bindings']['tab_id']])) is None:
            return {'task_id': task, 'status': 'unknown', 'resubmit': False}
        # Closing is not evidence of absence; reconcile with one bounded read.
        value = self._call([str(self.herdr), 'tab', 'get', record['bindings']['tab_id']])
        error = value.get('error', {}) if value else {}
        if not isinstance(error, dict) or error.get('code') != 'tab_not_found':
            return {'task_id': task, 'status': 'unknown', 'resubmit': False}
        return self._report(self.ledger.update(task, 'closed', 'cleanup_intent'))
