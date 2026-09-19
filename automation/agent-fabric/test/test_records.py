import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'lib'))
from records import write_event
class RecordsTests(unittest.TestCase):
 def test_writes_sanitized_local_jsonl(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'event.jsonl'; write_event(path, {'event_type':'preflight','details':{'host_alias':'safe','password':'no'}})
   data=json.loads(path.read_text()); self.assertEqual(data['details'], {'host_alias':'safe'}); self.assertEqual(data['record_version'],1)
 def test_rejects_protected_destination(self):
  with self.assertRaises(ValueError): write_event('/Users/leo/projects/event.jsonl', {'event_type':'x'})
if __name__=='__main__': unittest.main()
