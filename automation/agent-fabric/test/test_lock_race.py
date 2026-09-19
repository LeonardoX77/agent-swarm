import multiprocessing, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'lib'))
from lock import LockStore

def acquire(root, start, queue, operation):
    start.wait()
    queue.put(LockStore(root).acquire({'protocol_version': 1, 'operation_id': operation, 'area_id': 'race-area', 'writer_label': operation, 'initiator_role': 'macbook'})['code'])

class LockRaceTests(unittest.TestCase):
    def test_atomic_mkdir_allows_exactly_one_winner(self):
        with tempfile.TemporaryDirectory() as directory:
            start, queue = multiprocessing.Event(), multiprocessing.Queue()
            workers = [multiprocessing.Process(target=acquire, args=(directory, start, queue, f'op-{index}')) for index in range(4)]
            for worker in workers: worker.start()
            start.set()
            results = [queue.get(timeout=5) for worker in workers]
            for worker in workers: worker.join(timeout=5)
            self.assertEqual(results.count('ACQUIRED'), 1)
            self.assertEqual(results.count('CONTENDED'), 3)

if __name__ == '__main__': unittest.main()
