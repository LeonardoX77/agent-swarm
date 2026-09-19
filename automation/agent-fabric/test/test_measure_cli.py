import json,subprocess,sys,tempfile,unittest
from pathlib import Path
CLI=Path(__file__).parents[1]/'bin'/'fabric-measure'
class MeasureCliTests(unittest.TestCase):
 def test_writes_only_explicit_local_record(self):
  with tempfile.TemporaryDirectory() as directory:
   output=Path(directory)/'measure.json'; result=subprocess.run([sys.executable,str(CLI),'--record',str(output),'--host-role','macbook','--network-label','lab'],text=True,capture_output=True)
   self.assertEqual(result.returncode,0); self.assertEqual(json.loads(output.read_text())['smb_configuration'],'unmodified')
 def test_rejects_apply(self):
  result=subprocess.run([sys.executable,str(CLI),'--apply'],text=True,capture_output=True); self.assertNotEqual(result.returncode,0); self.assertIn('APPLY_NOT_IMPLEMENTED',result.stdout)
if __name__=='__main__': unittest.main()
