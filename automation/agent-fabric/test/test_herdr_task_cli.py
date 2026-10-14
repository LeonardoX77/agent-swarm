import contextlib
import importlib.machinery
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'lib'))
from herdr_task import Controller


class RecoverWaitTests(unittest.TestCase):
    def test_wait_recover_polls_every_two_seconds_without_side_effects(self):
        controller = object.__new__(Controller)
        reports = [
            {'task_id': 'task', 'status': 'pending', 'resubmit': False},
            {'task_id': 'task', 'status': 'pending', 'resubmit': False},
            {'task_id': 'task', 'status': 'done', 'resubmit': False},
        ]
        calls, sleeps = [], []
        clock_values = iter((0, 0, 2, 2, 4))
        controller.recover = lambda task: calls.append(task) or reports.pop(0)

        report = controller.wait_recover('task', 120, clock=lambda: next(clock_values), sleep=sleeps.append)

        self.assertEqual(report['status'], 'done')
        self.assertEqual(calls, ['task', 'task', 'task'])
        self.assertEqual(sleeps, [2, 2])

    def test_wait_recover_zero_is_a_single_read_and_timeout_retains_pending(self):
        controller = object.__new__(Controller)
        controller.recover = lambda task: {'task_id': task, 'status': 'pending', 'resubmit': False}
        self.assertEqual(controller.wait_recover('task', 0), {'task_id': 'task', 'status': 'pending', 'resubmit': False})

        controller.recover = lambda task: {'task_id': task, 'status': 'pending', 'resubmit': False}
        clock_values = iter((0, 0, 2))
        report = controller.wait_recover('task', 2, clock=lambda: next(clock_values), sleep=lambda _: None)
        self.assertEqual(report, {'task_id': 'task', 'status': 'pending', 'resubmit': False, 'timed_out': True})

    def test_wait_recover_interrupt_returns_last_report(self):
        controller = object.__new__(Controller)
        controller.recover = lambda task: {'task_id': task, 'status': 'pending', 'resubmit': False}
        report = controller.wait_recover('task', 2, clock=iter((0, 0)).__next__, sleep=lambda _: (_ for _ in ()).throw(KeyboardInterrupt()))
        self.assertEqual(report, {'task_id': 'task', 'status': 'pending', 'resubmit': False, 'interrupted': True})


class CliTests(unittest.TestCase):
    @staticmethod
    def module():
        path = Path(__file__).parents[1] / 'bin' / 'fabric-herdr-task'
        return importlib.machinery.SourceFileLoader('fabric_herdr_task_cli', str(path)).load_module()

    def invoke(self, argv, controller):
        module = self.module()
        stdout = io.StringIO()
        with patch.object(module, 'Controller', return_value=controller), patch.object(sys, 'argv', ['fabric-herdr-task', *argv]), contextlib.redirect_stdout(stdout):
            code = module.main()
        return code, json.loads(stdout.getvalue())

    def test_recover_default_wait_and_invalid_wait_are_typed(self):
        waits = []
        controller = type('Controller', (), {'wait_recover': lambda self, task, wait: waits.append(wait) or {'task_id': task, 'status': 'pending', 'resubmit': False}})()
        code, report = self.invoke(['recover', '550e8400-e29b-41d4-a716-446655440000'], controller)
        self.assertEqual((code, report['status'], waits), (0, 'pending', [120]))

        code, report = self.invoke(['recover', '550e8400-e29b-41d4-a716-446655440000', '--wait', '901'], controller)
        self.assertEqual((code, report), (2, {'status': 'failed', 'diagnostic_code': 'INVALID_WAIT'}))

    def test_recover_interrupt_has_last_report_and_exit_130(self):
        controller = type('Controller', (), {'wait_recover': lambda self, task, wait: {'task_id': task, 'status': 'pending', 'resubmit': False, 'interrupted': True}})()
        code, report = self.invoke(['recover', '550e8400-e29b-41d4-a716-446655440000'], controller)
        self.assertEqual((code, report['interrupted'], report['status']), (130, True, 'pending'))

    def test_unexpected_exception_is_typed_without_traceback(self):
        controller = type('Controller', (), {'wait_recover': lambda *_: (_ for _ in ()).throw(RuntimeError('network'))})()
        code, report = self.invoke(['recover', '550e8400-e29b-41d4-a716-446655440000', '--wait', '0'], controller)
        self.assertEqual((code, report), (2, {'status': 'failed', 'diagnostic_code': 'UNEXPECTED_ERROR:RuntimeError'}))


if __name__ == '__main__':
    unittest.main()
