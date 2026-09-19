import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'lib'))
from lock import LockStore
class LockTests(unittest.TestCase):
 def test_acquire_contention_release_and_epoch_fencing(self):
  with tempfile.TemporaryDirectory() as directory:
   store=LockStore(directory); first=store.acquire({'protocol_version':1,'operation_id':'op1','area_id':'coding-agent','writer_label':'one','initiator_role':'macbook'})
   self.assertEqual(first['code'],'ACQUIRED'); self.assertEqual(store.acquire({'protocol_version':1,'operation_id':'op2','area_id':'coding-agent','writer_label':'two','initiator_role':'mac-mini'})['code'],'CONTENDED')
   self.assertEqual(store.check('coding-agent','op1',first['epoch'])['code'],'ACQUIRED'); self.assertEqual(store.release('op1',first['capability'])['code'],'RELEASED'); self.assertEqual(store.check('coding-agent','op1',first['epoch'])['code'],'NOT_OWNER')
 def test_rejects_malformed_and_wrong_capability(self):
  with tempfile.TemporaryDirectory() as directory:
   store=LockStore(directory); self.assertEqual(store.acquire({})['code'],'INVALID_REQUEST'); lock=store.acquire({'protocol_version':1,'operation_id':'op1','area_id':'area','writer_label':'one','initiator_role':'macbook'}); self.assertEqual(store.release('op1','wrong')['code'],'NOT_OWNER')
if __name__=='__main__': unittest.main()
