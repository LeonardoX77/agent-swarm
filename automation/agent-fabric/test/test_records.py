import json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parents[1] / 'lib'))
from records import local_destination, write_event
class RecordsTests(unittest.TestCase):
 def test_writes_sanitized_local_jsonl(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'event.jsonl'; write_event(path, {'event_type':'preflight','details':{'host_alias':'safe','password':'no'}})
   data=json.loads(path.read_text()); self.assertEqual(data['details'], {'host_alias':'safe'}); self.assertEqual(data['record_version'],1)
 def test_allows_delivered_activity_destinations_for_their_effective_users(self):
  hosts = Path(__file__).parents[3] / 'config'
  for role, user in (('macbook', 'leo'), ('mac-mini', 'jarvis')):
   destination = json.loads((hosts / role / 'host.json').read_text(encoding='utf-8'))['activity_record']
   with patch('records.effective_user', return_value=user): self.assertTrue(local_destination(destination))
  with patch('records.effective_user', return_value='leo'):
   self.assertTrue(local_destination('/Users/leo/Library/Logs/AgentFabric/activity.jsonl'))

 def test_rejects_shared_other_user_and_ambiguous_destinations(self):
  with patch('records.effective_user', return_value='leo'):
   for destination in ('/Users/jarvis/.local/state/agent-fabric/activity.jsonl', '/Users/leo/projects/activity.jsonl', '/Volumes/agent-projects/activity.jsonl'):
    self.assertFalse(local_destination(destination))
   with tempfile.TemporaryDirectory() as directory:
    link = Path(directory) / 'link'
    link.symlink_to(Path(directory).parent)
    self.assertFalse(local_destination(link / 'activity.jsonl'))

 def test_rejects_protected_destination(self):
  with self.assertRaises(ValueError): write_event('/Users/leo/projects/event.jsonl', {'event_type':'x'})
if __name__=='__main__': unittest.main()
