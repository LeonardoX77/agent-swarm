import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'lib'))
from lock import LockStore
REQUEST={'protocol_version':1,'operation_id':'op1','area_id':'area','writer_label':'one','initiator_role':'macbook'}
class RecoveryTests(unittest.TestCase):
 def test_recovery_requires_every_inspection_finding(self):
  with tempfile.TemporaryDirectory() as directory:
   store=LockStore(directory); store.acquire(REQUEST)
   self.assertEqual(store.recover('area',{})['code'],'INSPECTION_REQUIRED')
   evidence={'terminal_or_stopped':True,'initiator_reachable_or_isolated':True,'no_active_write':True,'area_inactive':True}
   self.assertEqual(store.recover('area',evidence)['code'],'RECOVERY_QUARANTINED')
 def test_old_heartbeat_is_not_automatic_recovery(self):
  with tempfile.TemporaryDirectory() as directory:
   store=LockStore(directory); store.acquire(REQUEST); self.assertEqual(store.inspect('area')['code'],'INSPECTION_REQUIRED')
if __name__=='__main__': unittest.main()
