"""Atomic local test-state lock protocol; production provisioning is deferred."""
import hashlib,json,os,secrets,shutil,time
from pathlib import Path
REQUIRED={'protocol_version','operation_id','area_id','writer_label','initiator_role'}
def result(code,**extra): return {'code':code,**extra}
class LockStore:
 def __init__(self,state_root): self.root=Path(state_root); self.root.mkdir(parents=True,exist_ok=True); (self.root/'released').mkdir(exist_ok=True); (self.root/'recovered').mkdir(exist_ok=True)
 def _path(self,area): return self.root/(hashlib.sha256(area.encode()).hexdigest()+'.lock')
 def acquire(self,request):
  if not isinstance(request,dict) or set(request)!=REQUIRED or request.get('protocol_version')!=1 or not all(isinstance(request.get(key),str) and request[key] for key in REQUIRED-{'protocol_version'}): return result('INVALID_REQUEST')
  path=self._path(request['area_id'])
  try: path.mkdir(mode=0o700)
  except FileExistsError: return result('CONTENDED')
  capability=secrets.token_urlsafe(32); epoch=time.time_ns(); metadata={**request,'created_at':time.time(),'heartbeat_at':time.time(),'epoch':epoch,'capability_sha256':hashlib.sha256(capability.encode()).hexdigest()}
  temporary=path/'metadata.tmp'; temporary.write_text(json.dumps(metadata)); os.chmod(temporary,0o600); os.replace(temporary,path/'metadata.json')
  return result('ACQUIRED',capability=capability,epoch=epoch)
 def _metadata(self,area):
  try: return json.loads((self._path(area)/'metadata.json').read_text())
  except (OSError,json.JSONDecodeError): return None
 def check(self,area,operation_id,epoch):
  metadata=self._metadata(area)
  if not metadata or metadata['operation_id']!=operation_id or metadata['epoch']!=epoch: return result('NOT_OWNER')
  return result('ACQUIRED',epoch=epoch)
 def release(self,operation_id,capability):
  for path in self.root.glob('*.lock'):
   try: metadata=json.loads((path/'metadata.json').read_text())
   except (OSError,json.JSONDecodeError): continue
   if metadata['operation_id']!=operation_id: continue
   if not secrets.compare_digest(metadata['capability_sha256'],hashlib.sha256(capability.encode()).hexdigest()): return result('NOT_OWNER')
   quarantine=self.root/'released'/(path.name+'.'+str(metadata['epoch'])); os.replace(path,quarantine); shutil.rmtree(quarantine); return result('RELEASED')
  return result('NOT_OWNER')
 def inspect(self,area):
  metadata=self._metadata(area)
  return result('INSPECTION_REQUIRED',metadata={key:metadata[key] for key in ('area_id','operation_id','epoch','heartbeat_at')} if metadata else None)
 def recover(self,area,evidence):
  required={'terminal_or_stopped','initiator_reachable_or_isolated','no_active_write','area_inactive'}
  if not isinstance(evidence,dict) or not all(evidence.get(key) is True for key in required): return result('INSPECTION_REQUIRED')
  path=self._path(area); metadata=self._metadata(area)
  if not metadata: return result('INSPECTION_REQUIRED')
  quarantine=self.root/'recovered'/(path.name+'.'+str(metadata['epoch'])); os.replace(path,quarantine); shutil.rmtree(quarantine); return result('RECOVERY_QUARANTINED',retired_epoch=metadata['epoch'])
