import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'lib'))
from measurements import build_measurement, adjustment_ready
class MeasurementTests(unittest.TestCase):
 def test_builds_pending_non_configuring_record(self):
  record=build_measurement('sha256:abc','macbook','lab')
  self.assertEqual(record['smb_configuration'],'unmodified'); self.assertEqual(record['review']['status'],'pending'); self.assertIn('latency_ms',record['probes'])
 def test_blocks_missing_or_pending_evidence(self):
  self.assertFalse(adjustment_ready([])); self.assertFalse(adjustment_ready([build_measurement('sha256:a','macbook','lab')]))
  one=build_measurement('sha256:a','macbook','lab'); two=build_measurement('sha256:a','mac-mini','lab'); one['review']['status']=two['review']['status']='approved'
  self.assertTrue(adjustment_ready([one,two]))
if __name__=='__main__': unittest.main()
