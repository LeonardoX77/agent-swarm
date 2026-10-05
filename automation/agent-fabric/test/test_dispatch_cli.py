import importlib.machinery
import importlib.util
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
CLI = ROOT / 'bin' / 'fabric-dispatch'
REQUEST = {'version': 1, 'request_id': '550e8400-e29b-41d4-a716-446655440000', 'workspace': 'mac-agent-fabric', 'relative_path': '.', 'prompt': 'Inspect.', 'runtime': 'pi', 'initiator': 'macbook', 'timeout_seconds': 30}
CONFIG = {'version': 1, 'role': 'macbook', 'expected_user': 'leo', 'max_timeout_seconds': 60, 'workspace_roots': {'mac-agent-fabric': '/tmp/workspace'}, 'ssh_aliases': {'mac-mini': 'agent-fabric-mac-mini'}, 'allowed_runtimes': ['pi', 'opencode', 'claude']}


def module():
    loader = importlib.machinery.SourceFileLoader('fabric_dispatch_test', str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    value = importlib.util.module_from_spec(spec)
    loader.exec_module(value)
    return value


class DispatchTests(unittest.TestCase):
    def test_sends_json_only_on_stdin_to_configured_alias(self):
        dispatch = module()
        completed = subprocess.CompletedProcess([], 0, '{"status":"succeeded"}', '')
        with patch.object(dispatch.process, 'run', return_value=completed) as run:
            result = dispatch.dispatch(REQUEST, CONFIG, 'mac-mini')
        self.assertEqual(result['status'], 'succeeded')
        self.assertEqual(run.call_args.args[0], ['ssh', '-T', '-o', 'BatchMode=yes', 'agent-fabric-mac-mini'])
        self.assertEqual(json.loads(run.call_args.kwargs['input']), REQUEST)

    def test_returns_bounded_remote_output_only_on_success(self):
        dispatch = module()
        completed = subprocess.CompletedProcess([], 0, '{"status":"succeeded","output":"destination result"}', 'remote stderr')
        with patch.object(dispatch.process, 'run', return_value=completed):
            self.assertEqual(dispatch.dispatch(REQUEST, CONFIG, 'mac-mini'), {'status': 'succeeded', 'output': 'destination result'})

    def test_rejects_unconfigured_alias_before_process(self):
        dispatch = module()
        with patch.object(dispatch.process, 'run') as run:
            with self.assertRaises(ValueError):
                dispatch.dispatch(REQUEST, CONFIG, 'not-configured')
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
