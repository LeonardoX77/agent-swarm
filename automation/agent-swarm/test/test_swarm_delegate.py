import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

import importlib.machinery
import importlib.util

ROOT = Path(__file__).parents[1]
CLI = ROOT / 'bin' / 'swarm-delegate'
sys.path.insert(0, str(ROOT / 'lib'))

REGISTRY = {
    'macbook': {'name': 'macbook', 'role': 'hub', 'ssh_alias': 'swarm-macbook', 'catalog_root': '/Users/leo/projects', 'repo': '/Users/leo/projects/leo/mac-agent-swarm', 'path': '/opt/homebrew/bin:/usr/bin:/bin', 'gui_cwd': '/Users/leo/tmp', 'runtimes': ['pi', 'claude']},
    'mac-mini': {'name': 'mac-mini', 'role': 'spoke', 'ssh_alias': 'swarm-mac-mini', 'catalog_root': '/Volumes/agent projects', 'repo': '/Volumes/agent projects/leo/mac-agent-swarm', 'path': '/opt/homebrew/bin:/usr/bin:/bin', 'gui_cwd': '/Users/leo/tmp', 'runtimes': ['pi']},
}
TASK = '550e8400-e29b-41d4-a716-446655440000'


class FakeRegistry:
    def get(self, name):
        if name not in REGISTRY:
            raise KeyError(name)
        return REGISTRY[name]

    def self_host(self, nodename):
        return REGISTRY['macbook'] if nodename == 'MacBookLeo' else None

    @property
    def hosts(self):
        return REGISTRY


def module():
    loader = importlib.machinery.SourceFileLoader('swarm_delegate_test', str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    value = importlib.util.module_from_spec(spec)
    loader.exec_module(value)
    return value


class SwarmDelegateTests(unittest.TestCase):
    def invoke(self, argv, runner, stdin=''):
        value = module()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = value.main(argv, runner=runner, registry=FakeRegistry(), nodename='MacBookLeo', stdin=io.StringIO(stdin))
        return code, json.loads(out.getvalue())

    @staticmethod
    def runner(returncode=0, stdout='{"status":"submitted"}\n', stderr=''):
        calls = []
        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, returncode, stdout, stderr)
        run.calls = calls
        return run

    def test_help_uses_real_subprocess(self):
        result = subprocess.run([sys.executable, str(CLI), "--help"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)

    def test_help_prints_usage_and_exits_zero_without_ssh(self):
        run = self.runner()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = module().main(['--help'], runner=run, registry=FakeRegistry(), nodename='MacBookLeo', stdin=io.StringIO(''))
        self.assertEqual(code, 0)
        for action in ('list', 'self', 'preflight', 'submit', 'recover', 'close'):
            self.assertIn(action, out.getvalue())
        self.assertEqual(run.calls, [])

    def test_list_and_self_mark_the_current_host(self):
        run = self.runner()
        code, result = self.invoke(['list'], run)
        self.assertEqual(code, 0)
        self.assertEqual(result['hosts'][0], {'name': 'mac-mini', 'role': 'spoke', 'ssh_alias': 'swarm-mac-mini', 'runtimes': ['pi'], 'self': False})
        self.assertEqual(result['self'], 'macbook')
        code, result = self.invoke(['self'], run)
        self.assertEqual((code, result['name']), (0, 'macbook'))

    def test_submit_passes_stdin_and_builds_exact_ssh_argv(self):
        run = self.runner()
        envelope = '{"task_id":"%s"}' % TASK
        code, result = self.invoke(['submit', 'mac-mini'], run, envelope)
        self.assertEqual((code, result), (0, {'status': 'submitted'}))
        self.assertEqual(run.calls[0][0], ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=4', 'swarm-mac-mini', "PATH=/opt/homebrew/bin:/usr/bin:/bin /usr/bin/python3 '/Volumes/agent projects/leo/mac-agent-swarm/automation/agent-swarm/bin/swarm-herdr-task' submit"])
        self.assertEqual(run.calls[0][1]['input'], envelope)

    def test_recover_and_close_quote_arguments_and_validate_uuid_wait(self):
        run = self.runner()
        code, _ = self.invoke(['recover', 'mac-mini', TASK, '--wait', '0'], run)
        self.assertEqual(code, 0)
        self.assertTrue(run.calls[0][0][-1].endswith('recover %s --wait 0' % TASK))
        code, _ = self.invoke(['close', 'mac-mini', TASK], run)
        self.assertEqual(code, 0)
        for argv in (['recover', 'mac-mini', 'bad'], ['recover', 'mac-mini', TASK, '--wait', '901']):
            code, result = self.invoke(argv, run)
            self.assertEqual((code, result['diagnostic_code']), (2, 'INVALID_INPUT'))

    def test_remote_json_failure_is_preserved_with_target(self):
        run = self.runner(returncode=1, stdout='{"status":"failed","diagnostic_code":"INVALID_ENVELOPE"}\n')
        code, result = self.invoke(['submit', 'mac-mini'], run, '{}')
        self.assertEqual((code, result), (1, {'status': 'failed', 'diagnostic_code': 'INVALID_ENVELOPE', 'target': 'mac-mini'}))

    def test_nonjson_remote_failure_includes_trimmed_output(self):
        run = self.runner(returncode=1, stdout='out-' + ('x' * 600), stderr='err-' + ('y' * 600))
        code, result = self.invoke(['submit', 'mac-mini'], run, '{}')
        self.assertEqual((code, result['status'], result['diagnostic_code'], result['target'], result['remote_exit']),
                         (1, 'failed', 'REMOTE_FAILURE', 'mac-mini', 1))
        self.assertEqual(len(result['remote_stdout']), 500)
        self.assertEqual(len(result['remote_stderr']), 500)

    def test_unreachable_preflight_hint_and_self_target_are_typed(self):
        run = self.runner(returncode=255)
        code, result = self.invoke(['submit', 'mac-mini'], run, '{}')
        self.assertEqual((code, result), (3, {'status': 'unreachable', 'target': 'mac-mini', 'resubmit_hint': 'recover or re-run submit with the identical envelope'}))
        run = self.runner(returncode=1)
        code, result = self.invoke(['preflight', 'mac-mini'], run)
        self.assertEqual((code, result['status'], result['hint']), (1, 'catalog_missing', 'run swarm-smb-mount mount on that host'))
        self.assertIn("test -x '/Volumes/agent projects/leo/mac-agent-swarm/automation/agent-swarm/bin/swarm-herdr-task' && test -d '/Volumes/agent projects'", run.calls[0][0][-1])
        code, result = self.invoke(['submit', 'macbook'], self.runner(), '{}')
        self.assertEqual((code, result['diagnostic_code']), (2, 'SELF_TARGET'))


if __name__ == '__main__':
    unittest.main()
