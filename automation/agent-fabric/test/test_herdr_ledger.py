import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'lib'))
from herdr_ledger import Ledger, LedgerConflict, LedgerCorrupt, UnsafeLedgerRoot

TASK = '550e8400-e29b-41d4-a716-446655440000'
PAYLOAD = {'user_prompt': 'Inspect focused findings.', 'planned_session_id': 'session-1', 'planned_agent': 'pi'}


class LedgerTests(unittest.TestCase):
    def test_reservation_payload_is_exact_and_bindings_pin_once(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory))
            self.assertEqual(ledger.reserve(TASK, PAYLOAD)['phase'], 'reserved')
            self.assertEqual(ledger.reserve(TASK, dict(PAYLOAD))['payload'], PAYLOAD)
            with self.assertRaises(LedgerConflict): ledger.reserve(TASK, {**PAYLOAD, 'planned_agent': 'other'})
            ledger.update(TASK, 'create_intent', 'reserved')
            created = ledger.update(TASK, 'created', 'create_intent', {'session_id': 'session-1', 'pane_id': 'pane-1'})
            self.assertEqual(created['bindings']['pane_id'], 'pane-1')
            with self.assertRaises(LedgerConflict): ledger.update(TASK, 'start_intent', 'created', {'pane_id': 'other'})

    def test_cas_allows_one_concurrent_transition_and_unknown_never_resubmits(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Ledger(Path(directory)), Ledger(Path(directory)); first.reserve(TASK, PAYLOAD)
            outcomes = []
            def transition(ledger):
                try: outcomes.append(ledger.update(TASK, 'create_intent', 'reserved')['phase'])
                except LedgerConflict: outcomes.append('conflict')
            threads = [threading.Thread(target=transition, args=(ledger,)) for ledger in (first, second)]
            for thread in threads: thread.start()
            for thread in threads: thread.join()
            self.assertEqual(sorted(outcomes), ['conflict', 'create_intent'])
            first.update(TASK, 'unknown', 'create_intent')
            self.assertEqual(first.update(TASK, 'recover_intent', 'unknown')['phase'], 'recover_intent')
            with self.assertRaises(LedgerConflict): first.update(TASK, 'submit_intent', 'recover_intent')

    def test_rejects_unsafe_lock_path_or_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); task_lock = root / ('.' + TASK + '.lock')
            task_lock.write_text(''); task_lock.chmod(0o644)
            with self.assertRaises(LedgerCorrupt): Ledger(root).reserve(TASK, PAYLOAD)
            task_lock.unlink(); task_lock.symlink_to(root / 'other')
            with self.assertRaises(LedgerCorrupt): Ledger(root).reserve(TASK, PAYLOAD)

    def test_private_regular_records_and_corruption_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); ledger = Ledger(root); ledger.reserve(TASK, PAYLOAD)
            path = root / (TASK + '.json')
            self.assertEqual(os.stat(root).st_mode & 0o777, 0o700)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            path.write_text('{'); path.chmod(0o600)
            with self.assertRaises(LedgerCorrupt): ledger.load(TASK)
            link = root / 'link'; link.symlink_to(root, target_is_directory=True)
            with self.assertRaises(UnsafeLedgerRoot): Ledger(link)


if __name__ == '__main__': unittest.main()
