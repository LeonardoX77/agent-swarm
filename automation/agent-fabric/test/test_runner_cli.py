import importlib.machinery
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from request import validate_request
CLI = ROOT / 'bin' / 'fabric-runner'
REQUEST = {'version': 1, 'request_id': '550e8400-e29b-41d4-a716-446655440000', 'workspace': 'mac-agent-fabric', 'relative_path': '.', 'prompt': 'Inspect.', 'initiator': 'macbook', 'timeout_seconds': 30}


def module():
    loader = importlib.machinery.SourceFileLoader('fabric_runner_test', str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    value = importlib.util.module_from_spec(spec)
    loader.exec_module(value)
    return value


class RunnerTests(unittest.TestCase):
    def test_rejects_relative_path_forms_for_schema_runtime_parity(self):
        for relative_path in ('', '/absolute', './child', 'child//leaf', 'child/./leaf', 'child/../leaf'):
            with self.assertRaises(ValueError):
                validate_request({**REQUEST, 'relative_path': relative_path})

    def test_schema_pattern_matches_runtime_relative_path_rules(self):
        schema = json.loads((ROOT / 'schema' / 'task-request.schema.json').read_text(encoding='utf-8'))
        pattern = schema['properties']['relative_path']['pattern']
        for relative_path in ('.', 'child', 'child/.hidden', 'child/leaf'):
            self.assertIsNotNone(re.fullmatch(pattern, relative_path))
        for relative_path in ('', '/absolute', './child', 'child//leaf', 'child/./leaf', 'child/../leaf'):
            self.assertIsNone(re.fullmatch(pattern, relative_path))

    def test_invokes_pi_with_resolved_cwd_and_safe_name(self):
        runner = module()
        with tempfile.TemporaryDirectory() as directory:
            config = {'version': 1, 'role': 'mac-mini', 'expected_user': 'jarvis', 'max_timeout_seconds': 60, 'workspace_roots': {'mac-agent-fabric': directory}, 'ssh_aliases': {}}
            with patch.dict(os.environ, {}, clear=True), patch.object(runner, 'effective_user', return_value='jarvis'), patch.object(runner.process, 'run', return_value=subprocess.CompletedProcess([], 0, 'done', '')) as run:
                result = runner.run_task(REQUEST, config)
        self.assertEqual(result['status'], 'succeeded')
        self.assertEqual(run.call_args.args[0][:5], ['pi', '-p', '--approve', '--name', 'fabric-550e8400-e29b-41d4-a716-446655440000'])
        self.assertEqual(run.call_args.kwargs['cwd'], str(Path(directory).resolve()))
        self.assertEqual(run.call_args.kwargs['timeout'], 30)
        self.assertEqual(run.call_args.kwargs['env'], {'PATH': runner.environment.SAFE_PATH})

    def test_rejects_dangerous_environment_before_invoking_mocked_pi(self):
        runner = module()
        with tempfile.TemporaryDirectory() as directory:
            config = {'version': 1, 'role': 'mac-mini', 'expected_user': 'jarvis', 'max_timeout_seconds': 60, 'workspace_roots': {'mac-agent-fabric': directory}, 'ssh_aliases': {}}
            with patch.dict(os.environ, {'NODE_OPTIONS': '--require injected'}, clear=True), patch.object(runner, 'effective_user', return_value='jarvis'), patch.object(runner.process, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'UNSAFE_ENVIRONMENT'):
                    runner.run_task(REQUEST, config)
            run.assert_not_called()

    def test_returns_utf8_bounded_stdout_without_stderr(self):
        runner = module()
        with tempfile.TemporaryDirectory() as directory:
            config = {'version': 1, 'role': 'mac-mini', 'expected_user': 'jarvis', 'max_timeout_seconds': 60, 'workspace_roots': {'mac-agent-fabric': directory}, 'ssh_aliases': {}}
            stdout = 'é' * (runner.process.MAX_OUTPUT_BYTES // 2 + 1)
            with patch.dict(os.environ, {}, clear=True), patch.object(runner, 'effective_user', return_value='jarvis'), patch.object(runner.process, 'run', return_value=subprocess.CompletedProcess([], 0, stdout, 'sensitive stderr')):
                result = runner.run_task(REQUEST, config)
        self.assertEqual(result['status'], 'succeeded')
        self.assertIn('output', result)
        self.assertLessEqual(len(result['output'].encode('utf-8')), runner.process.MAX_OUTPUT_BYTES)
        self.assertNotIn('stderr', result)
        self.assertNotIn('sensitive', result['output'])

    def test_surfaces_activity_record_failure_as_warning_without_retrying(self):
        runner = module()
        with tempfile.TemporaryDirectory() as directory:
            config = {'version': 1, 'role': 'mac-mini', 'expected_user': 'jarvis', 'max_timeout_seconds': 60, 'workspace_roots': {'mac-agent-fabric': directory}, 'ssh_aliases': {}, 'activity_record': '/var/log/fabric.jsonl'}
            with patch.dict(os.environ, {}, clear=True), patch.object(runner, 'effective_user', return_value='jarvis'), patch.object(runner.process, 'run', return_value=subprocess.CompletedProcess([], 0, 'done', '')), patch.object(runner, 'write_event', side_effect=OSError('unavailable')) as write:
                result = runner.run_task(REQUEST, config)
        self.assertEqual(result['status'], 'succeeded')
        self.assertEqual(result['warnings'], ['ACTIVITY_RECORD_FAILED'])
        self.assertEqual(write.call_count, 2)
        terminal_event = write.call_args_list[1].args[1]
        self.assertEqual(terminal_event['host_role'], 'mac-mini')
        self.assertEqual(terminal_event['diagnostic_code'], 'NONE')
        self.assertGreaterEqual(terminal_event['duration_seconds'], 0)

    def test_rejects_ssh_original_command_and_symlink_escape_before_pi(self):
        runner = module()
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory).parent
            (Path(directory) / 'escape').symlink_to(outside)
            config = {'version': 1, 'role': 'mac-mini', 'expected_user': 'jarvis', 'max_timeout_seconds': 60, 'workspace_roots': {'mac-agent-fabric': directory}, 'ssh_aliases': {}}
            with patch.dict(os.environ, {'SSH_ORIGINAL_COMMAND': 'bad'}), patch.object(runner, 'effective_user', return_value='jarvis'), patch.object(runner.process, 'run') as run:
                with self.assertRaises(ValueError): runner.run_task(REQUEST, config)
            with patch.dict(os.environ, {}, clear=True), patch.object(runner, 'effective_user', return_value='jarvis'), patch.object(runner.process, 'run') as run:
                with self.assertRaises(ValueError): runner.run_task({**REQUEST, 'relative_path': 'escape'}, config)
            run.assert_not_called()

    def test_rejects_wrong_effective_user_before_invoking_pi(self):
        runner = module()
        with tempfile.TemporaryDirectory() as directory:
            config = {'version': 1, 'role': 'mac-mini', 'expected_user': 'jarvis', 'max_timeout_seconds': 60, 'workspace_roots': {'mac-agent-fabric': directory}, 'ssh_aliases': {}}
            with patch.dict(os.environ, {}, clear=True), patch.object(runner, 'effective_user', return_value='leo'), patch.object(runner.process, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'UNEXPECTED_USER'):
                    runner.run_task(REQUEST, config)
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
