"""Synthetic, non-configuring baseline evidence."""
from datetime import datetime, timezone

def build_measurement(fingerprint, host_role, network_label):
 return {'record_version':1,'recorded_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'plan_fingerprint':fingerprint,'host_role':host_role,'environment':{'network_label':network_label},'fixture_version':'representative-tree-v1','probes':{'reachability':{'attempts':20,'successes':20},'latency_ms':{'p50':0.0,'p95':0.0,'max':0.0},'throughput_mib_s':{'direction':'read','samples':[0.0]},'workspace_smb':{'fixture':'representative-tree-v1','operations':[{'name':'metadata-walk','duration_ms':0,'outcome':'pass'},{'name':'small-file-read-write','duration_ms':0,'outcome':'pass'},{'name':'git-status','duration_ms':0,'outcome':'pass'}]}},'smb_configuration':'unmodified','review':{'status':'pending','reviewed_at':None,'decision':None}}
def adjustment_ready(records):
 if len(records)<2: return False
 roles={record.get('host_role') for record in records}
 return roles=={'macbook','mac-mini'} and all(record.get('review',{}).get('status')=='approved' and all(key in record.get('probes',{}) for key in ('reachability','latency_ms','throughput_mib_s','workspace_smb')) for record in records)
