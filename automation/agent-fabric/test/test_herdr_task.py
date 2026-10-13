import json
import os
import subprocess
import sys
import tempfile
import threading
import re
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'lib'))
import herdr_task
from herdr_task import Controller, TaskError

TASK = '550e8400-e29b-41d4-a716-446655440000'
ENVELOPE = {'task_id': TASK, 'origin_host': 'MacBookLeo', 'project': 'leo/mac-agent-fabric', 'goal': 'Inspect focused findings.', 'acceptance': 'Return findings.', 'mode': 'executor'}


def response(value, code=0, stderr=''):
    return subprocess.CompletedProcess([], code, json.dumps(value), stderr)

def stderr_response(value, code=1):
    return subprocess.CompletedProcess([], code, '', json.dumps(value))


class Herdr:
    def __init__(self, session):
        self.calls, self.session = [], session
        self.tab = {'tab_id': 'tab-1', 'pane_id': 'pane-1'}
        # Recorded live schema: no id/agent_id; agent_session carries the runtime too.
        self.agent = {'agent': 'pi', 'name': None, 'pane_id': 'pane-1', 'tab_id': 'tab-1', 'agent_status': 'idle', 'agent_session': {'agent': 'pi', 'kind': 'path', 'source': 'herdr:pi', 'value': str(session)}}
        self.fail = None
        self.prompt_failure = None
        self.tab_get_error = None
        self.tab_get_response = None
        self.strict_name = True
    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        if self.fail and argv[1:3] == self.fail: raise subprocess.TimeoutExpired(argv, 1)
        command = argv[1:3]
        if command == ['tab', 'create']:
            return response({'result': {'tab': {'tab_id': 'tab-1'}, 'root_pane': {'pane_id': 'pane-1'}}})
        if command == ['agent', 'start']:
            if self.strict_name and not re.fullmatch(r'[a-z][a-z0-9_-]{0,31}', argv[3]):
                return stderr_response({'error': {'code': 'invalid_agent_name'}})
            self.agent['name'] = argv[3]
            self.agent['agent_session']['value'] = argv[-1]
            return response({'result': {'agent': self.agent}})
        if command == ['agent', 'get']:
            return response({'result': {'agent': self.agent}})
        if command == ['agent', 'prompt']:
            if self.prompt_failure is not None:
                return self.prompt_failure
            if '--timeout' in argv and '--wait' not in argv:
                return subprocess.CompletedProcess([], 2, '', '--timeout requires --wait')
            return response({'result': {'type': 'agent_prompted', 'agent': self.agent}})
        if command == ['tab', 'get']:
            if self.tab_get_response is not None:
                return self.tab_get_response
            if self.tab_get_error:
                return stderr_response({'error': {'code': self.tab_get_error}})
            return response({'result': {'tab': {'tab_id': 'tab-1'}}})
        if command == ['tab', 'close']:
            return response({'result': {'closed': True}})
        raise AssertionError(argv)


class HerdrTaskTests(unittest.TestCase):
    def make(self):
        directory = tempfile.TemporaryDirectory(); root = Path(directory.name); state = root / 'state'; catalog = root / 'projects'; project = catalog / 'leo' / 'mac-agent-fabric'; project.mkdir(parents=True); gui = root / 'gui'; gui.mkdir()
        binary = root / 'herdr'; binary.write_text('#!/bin/sh\n'); binary.chmod(0o700)
        session = state / 'sessions' / TASK / 'session.jsonl'; herdr = Herdr(session)
        controller = Controller(state, herdr=binary, project_root=catalog, hostname='MacBookLeo-test', gui_cwd=gui, run=herdr)
        return directory, controller, herdr, session

    def test_envelope_has_six_fields_and_accepts_executor_mode_only(self):
        self.assertEqual(herdr_task._envelope(ENVELOPE), ENVELOPE)
        for extra in ({'executor': 'pi'}, {'unexpected': 'value'}):
            with self.subTest(extra=extra), self.assertRaisesRegex(TaskError, 'INVALID_ENVELOPE'):
                herdr_task._envelope({**ENVELOPE, **extra})
        with self.assertRaisesRegex(TaskError, 'UNSUPPORTED_MODE'):
            herdr_task._envelope({**ENVELOPE, 'mode': 'orchestrator'})
        for mode in ('host-local', 'other'):
            with self.subTest(mode=mode), self.assertRaisesRegex(TaskError, 'UNSUPPORTED_MODE'):
                herdr_task._envelope({**ENVELOPE, 'mode': mode})

    def test_submit_uses_owned_resources_and_duplicate_is_single_effect(self):
        directory, controller, herdr, session = self.make()
        with directory:
            first = controller.submit(ENVELOPE); second = controller.submit(dict(ENVELOPE))
            self.assertEqual((first['status'], second['status']), ('submitted', 'submitted'))
            self.assertRegex(controller.ledger.load(TASK)['payload']['planned_agent'], r'^p[a-f0-9]{31}$')
            self.assertEqual([call[1:3] for call in herdr.calls], [['tab', 'create'], ['agent', 'start'], ['agent', 'get'], ['agent', 'prompt']])
            self.assertEqual(oct(os.stat(session.parent).st_mode & 0o777), '0o700')
            self.assertEqual(oct(os.stat(session).st_mode & 0o777), '0o600')
            header = json.loads(session.read_text())
            self.assertEqual((header['type'], header['version'], header['id'], header['cwd']), ('session', 3, TASK, str(controller.gui_cwd)))
            self.assertEqual(herdr.calls[0][herdr.calls[0].index('--cwd') + 1], str(controller.gui_cwd))
            self.assertIn('timestamp', header)
            self.assertEqual(controller.ledger.load(TASK)['bindings']['agent_id'], 'pane-1')
            self.assertIn('--session', herdr.calls[1])
            self.assertEqual(Path(herdr.calls[1][-1]).resolve(), session.resolve())

    def test_prompt_argv_never_uses_timeout_without_wait_and_is_submitted(self):
        directory, controller, herdr, _ = self.make()
        with directory:
            report = controller.submit(ENVELOPE)
            prompt = next(call for call in herdr.calls if call[1:3] == ['agent', 'prompt'])
            self.assertFalse('--timeout' in prompt and '--wait' not in prompt)
            self.assertNotIn('--timeout', prompt)
            self.assertNotIn('--wait', prompt)
            self.assertEqual(report['status'], 'submitted')

    def test_submit_failure_reports_transient_truncated_last_error_without_retry(self):
        for returncode, stderr in ((0, 'plain stderr failure'), (2, 'x' * 400)):
            with self.subTest(returncode=returncode):
                directory, controller, herdr, _ = self.make()
                with directory:
                    herdr.prompt_failure = subprocess.CompletedProcess([], returncode, '', stderr)
                    report = controller.submit(ENVELOPE)
                    self.assertEqual(report['status'], 'unknown')
                    self.assertEqual(report['last_error']['returncode'], returncode)
                    self.assertEqual(report['last_error']['stderr'], stderr[:300])
                    self.assertLessEqual(len(report['last_error']['stderr']), 300)
                    self.assertNotIn('last_error', controller.ledger.load(TASK))
                    calls = len(herdr.calls)
                    self.assertEqual(controller.submit(ENVELOPE)['status'], 'unknown')
                    self.assertEqual(len(herdr.calls), calls)

    def test_changed_payload_rejected_and_concurrent_submit_has_one_effect(self):
        directory, controller, herdr, _ = self.make()
        with directory:
            results = []
            threads = [threading.Thread(target=lambda: results.append(controller.submit(ENVELOPE))) for _ in range(2)]
            for thread in threads: thread.start()
            for thread in threads: thread.join()
            self.assertEqual(len([call for call in herdr.calls if call[1:3] == ['tab', 'create']]), 1)
            with self.assertRaises(TaskError): controller.submit({**ENVELOPE, 'goal': 'Changed.'})

    def test_ambiguous_effects_become_unknown_without_retry(self):
        for command in (['tab', 'create'], ['agent', 'start'], ['agent', 'prompt']):
            directory, controller, herdr, _ = self.make()
            with directory:
                herdr.fail = command
                self.assertEqual(controller.submit(ENVELOPE)['status'], 'unknown')
                count = len(herdr.calls); self.assertEqual(controller.submit(ENVELOPE)['status'], 'unknown')
                self.assertEqual(len(herdr.calls), count)

    def test_recover_is_readonly_and_requires_owned_identity_and_session_chain(self):
        directory, controller, herdr, session = self.make()
        with directory:
            controller.submit(ENVELOPE)
            prompt = controller.ledger.load(TASK)['payload']['user_prompt']
            entries = [json.loads(session.read_text()),
                {'type':'message','id':'user','parentId':None,'message':{'role':'user','content':prompt}},
                {'type':'message','id':'answer','parentId':'user','message':{'role':'assistant','content':[{'type':'text','text':'Done'}],'stopReason':'stop'}}]
            session.write_text('\n'.join(json.dumps(x) for x in entries) + '\n'); session.chmod(0o600)
            herdr.agent['agent_session']['value'] = '/foreign/session.jsonl'
            self.assertEqual(controller.recover(TASK)['status'], 'unknown')
            herdr.agent['agent_session']['value'] = str(controller._session_path(TASK))
            self.assertEqual(controller.recover(TASK)['resulttext'], 'Done')
            self.assertNotIn(['agent', 'prompt'], [call[1:3] for call in herdr.calls[4:]])

    def test_recover_reports_transient_session_parser_error(self):
        directory, controller, _, session = self.make()
        with directory:
            controller.submit(ENVELOPE)
            session.write_text('{bad json}\n'); session.chmod(0o600)
            report = controller.recover(TASK)
            self.assertEqual(report['status'], 'unknown')
            self.assertEqual(report['last_error'], {'session_error': 'MalformedSession:MALFORMED_JSONL'})
            self.assertNotIn('last_error', controller.ledger.load(TASK))

    def test_close_requires_final_owned_result_and_never_cancels_working(self):
        directory, controller, herdr, session = self.make()
        with directory:
            controller.submit(ENVELOPE)
            self.assertEqual(controller.close(TASK)['status'], 'refused')
            herdr.agent['agent_status'] = 'working'
            self.assertEqual(controller.close(TASK)['status'], 'refused')
            self.assertNotIn(['tab', 'close'], [call[1:3] for call in herdr.calls])

    def test_cli_rejects_oversize_stdin_before_json_parsing(self):
        directory, controller, _, _ = self.make()
        with directory:
            cli = Path(__file__).parents[1] / 'bin' / 'fabric-herdr-task'
            completed = subprocess.run([str(cli), 'submit', '--state-dir', str(controller.state), '--project-root', str(controller.project), '--herdr', str(controller.herdr)], input=b'x' * 65537, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(json.loads(completed.stdout)['diagnostic_code'], 'INPUT_TOO_LARGE')

    def test_preserves_typed_nonzero_api_error_without_accepting_it_as_result(self):
        directory, controller, _, _ = self.make()
        with directory:
            controller.run = lambda *_a, **_k: stderr_response({'error': {'code': 'tab_not_found'}})
            value = controller._call([str(controller.herdr), 'tab', 'get', 'tab-1'])
            self.assertEqual(value, {'error': {'code': 'tab_not_found'}})
            self.assertIsNone(controller._result(value))

    def test_close_requires_typed_post_close_absence_and_never_retries_close(self):
        directory, controller, herdr, session = self.make()
        with directory:
            controller.submit(ENVELOPE)
            prompt = controller.ledger.load(TASK)['payload']['user_prompt']
            entries = [json.loads(session.read_text()), {'type':'message','id':'user','parentId':None,'message':{'role':'user','content':prompt}}, {'type':'message','id':'answer','parentId':'user','message':{'role':'assistant','content':[{'type':'text','text':'Done'}],'stopReason':'stop'}}]
            session.write_text('\n'.join(json.dumps(x) for x in entries) + '\n'); session.chmod(0o600)
            self.assertEqual(controller.recover(TASK)['status'], 'done')
            self.assertEqual(controller.close(TASK)['status'], 'unknown')
            close_count = len([call for call in herdr.calls if call[1:3] == ['tab', 'close']])
            herdr.tab_get_error = 'not_found'
            self.assertEqual(controller.close(TASK)['status'], 'unknown')
            self.assertEqual(len([call for call in herdr.calls if call[1:3] == ['tab', 'close']]), close_count)
            herdr.tab_get_error = 'tab_not_found'
            self.assertEqual(controller.close(TASK)['status'], 'closed')

    def test_nonzero_tab_get_typed_errors_from_both_streams_reconcile_only_tab_not_found(self):
        for stream in ('stdout', 'stderr'):
            directory, controller, herdr, session = self.make()
            with self.subTest(stream=stream), directory:
                controller.submit(ENVELOPE)
                prompt = controller.ledger.load(TASK)['payload']['user_prompt']
                entries = [json.loads(session.read_text()), {'type':'message','id':'user','parentId':None,'message':{'role':'user','content':prompt}}, {'type':'message','id':'answer','parentId':'user','message':{'role':'assistant','content':[{'type':'text','text':'Done'}],'stopReason':'stop'}}]
                session.write_text('\n'.join(json.dumps(x) for x in entries) + '\n'); session.chmod(0o600)
                controller.recover(TASK)
                controller.ledger.update(TASK, 'cleanup_intent', 'result')
                envelope = json.dumps({'error': {'code': 'tab_not_found'}})
                herdr.tab_get_response = subprocess.CompletedProcess([], 1, envelope if stream == 'stdout' else '', envelope if stream == 'stderr' else '')
                self.assertEqual(controller.close(TASK)['status'], 'closed')
                self.assertEqual(controller.ledger.load(TASK)['phase'], 'closed')
                self.assertEqual(len([call for call in herdr.calls if call[1:3] == ['tab', 'close']]), 0)
        for response_value in (stderr_response({'error': {'code': 'not_found'}}), subprocess.CompletedProcess([], 1, '', 'not json')):
            directory, controller, herdr, _ = self.make()
            with self.subTest(response=response_value), directory:
                controller.submit(ENVELOPE)
                controller.ledger.update(TASK, 'result', 'submitted')
                controller.ledger.update(TASK, 'cleanup_intent', 'result')
                herdr.tab_get_response = response_value
                self.assertEqual(controller.close(TASK)['status'], 'unknown')
                self.assertEqual(controller.ledger.load(TASK)['phase'], 'cleanup_intent')
                self.assertEqual(len([call for call in herdr.calls if call[1:3] == ['tab', 'close']]), 0)

    def test_reports_retained_session_result_after_cleanup_and_close(self):
        directory, controller, herdr, session = self.make()
        with directory:
            controller.submit(ENVELOPE)
            prompt = controller.ledger.load(TASK)['payload']['user_prompt']
            entries = [json.loads(session.read_text()), {'type':'message','id':'user','parentId':None,'message':{'role':'user','content':prompt}}, {'type':'message','id':'answer','parentId':'user','message':{'role':'assistant','content':[{'type':'text','text':'Done'}],'stopReason':'stop'}}]
            session.write_text('\n'.join(json.dumps(x) for x in entries) + '\n'); session.chmod(0o600)
            self.assertEqual(controller.recover(TASK)['status'], 'done')
            controller.ledger.update(TASK, 'cleanup_intent', 'result')
            cleanup = controller.recover(TASK)
            self.assertEqual(cleanup, {'task_id': TASK, 'status': 'cleanup_intent', 'resulttext': 'Done', 'userentry': 'user', 'assistantentry': 'answer', 'resubmit': False})
            herdr.tab_get_response = stderr_response({'error': {'code': 'tab_not_found'}})
            self.assertEqual(controller.close(TASK)['status'], 'closed')
            calls = len(herdr.calls)
            expected = {'task_id': TASK, 'status': 'closed', 'resulttext': 'Done', 'userentry': 'user', 'assistantentry': 'answer', 'resubmit': False}
            self.assertEqual(controller.recover(TASK), expected)
            self.assertEqual(controller.close(TASK), expected)
            self.assertEqual(len(herdr.calls), calls)

    def test_catalog_project_validation_handles_nested_default_explicit_and_escapes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); state = root / 'state'; catalog = root / 'catalog'; child = catalog / 'leo' / 'mac-agent-fabric'; child.mkdir(parents=True); gui = root / 'gui'; gui.mkdir(); binary = root / 'herdr-real'; binary.write_text(''); binary.chmod(0o700); link = root / 'herdr'; link.symlink_to(binary)
            with self.assertRaises(TaskError): Controller(state, herdr=binary, hostname='OtherHost', gui_cwd=gui, run=lambda *_a, **_k: None)
            with self.assertRaises(TaskError): Controller(state, herdr=binary, project_root=root / '..', hostname='MacBookLeo', gui_cwd=gui, run=lambda *_a, **_k: None)
            session = state / 'sessions' / TASK / 'session.jsonl'; fake = Herdr(session)
            self.assertEqual(Controller(state, herdr=link, project_root=catalog, hostname='OtherHost', gui_cwd=gui, run=fake).submit(ENVELOPE)['status'], 'submitted')
            default_task = {**ENVELOPE, 'task_id': '550e8400-e29b-41d4-a716-446655440003'}
            default_session = root / 'state-default' / 'sessions' / default_task['task_id'] / 'session.jsonl'
            with patch.dict(herdr_task._HOST_ROOTS, {'MacMiniLeo': catalog}, clear=True):
                self.assertEqual(Controller(root / 'state-default', herdr=binary, hostname='MacMiniLeo-test', gui_cwd=gui, run=Herdr(default_session)).submit(default_task)['status'], 'submitted')
            missing = {**ENVELOPE, 'task_id': '550e8400-e29b-41d4-a716-446655440001', 'project': 'leo/missing'}
            with self.assertRaises(TaskError): Controller(root / 'state2', herdr=binary, project_root=catalog, hostname='OtherHost', gui_cwd=gui, run=lambda *_a, **_k: None).submit(missing)
            (catalog / 'escape').symlink_to(root, target_is_directory=True)
            escaped = {**ENVELOPE, 'task_id': '550e8400-e29b-41d4-a716-446655440002', 'project': 'escape'}
            with self.assertRaises(TaskError): Controller(root / 'state3', herdr=binary, project_root=catalog, hostname='OtherHost', gui_cwd=gui, run=lambda *_a, **_k: None).submit(escaped)


if __name__ == '__main__': unittest.main()
