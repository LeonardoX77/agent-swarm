import json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]; CLI=ROOT/'bin'/'fabric-preflight'
PLAN={"schema_version":1,"macbook":{"ssh_host_alias":"agent-fabric-macbook","workspace_share_root":"/Users/leo/projects","future_share_name":"agent-workspaces","lock_root":"/Users/Shared/agent-fabric/locks"},"mac_mini":{"ssh_host_alias":"agent-fabric-macbook","future_mount_target":"/Volumes/agent-workspaces","execution_identity":"fabric-runner"},"workspace_areas":[{"id":"coding-agent","relative_path":"packages/coding-agent"}],"skills":{"transport":"git","repository_url":"https://example.invalid/org/shared-skills.git","local_clone_roots":{"macbook":"/opt/agent-fabric/skills","mac_mini":"/opt/agent-fabric/skills"}}}
class PreflightTests(unittest.TestCase):
 def test_dry_run_and_safe_record(self):
  with tempfile.TemporaryDirectory() as directory:
   config=Path(directory)/'plan.json'; record=Path(directory)/'record.jsonl'; config.write_text(json.dumps(PLAN))
   result=subprocess.run([sys.executable,str(CLI),'--config',str(config),'--record',str(record)],text=True,capture_output=True)
   self.assertEqual(result.returncode,0); self.assertIn('mode: dry-run',result.stdout); self.assertTrue(record.exists())
 def test_apply_is_not_implemented(self):
  result=subprocess.run([sys.executable,str(CLI),'--apply'],text=True,capture_output=True)
  self.assertNotEqual(result.returncode,0); self.assertIn('APPLY_NOT_IMPLEMENTED',result.stdout)
if __name__=='__main__': unittest.main()
