"""Safe, local-only evidence records."""
import json, os
from datetime import datetime, timezone
from pathlib import Path
FORBIDDEN = ("password", "secret", "token", "private", "keychain", "command", "stderr", "environment", "path")
def _safe(value):
 if isinstance(value,dict): return {k:_safe(v) for k,v in value.items() if not any(word in k.lower() for word in FORBIDDEN)}
 if isinstance(value,list): return [_safe(item) for item in value]
 return value
def _local(path):
 text=str(path)
 return not (text.startswith('/Users/leo/projects') or text.startswith('/Volumes/') or '/Users/' in text)
def write_event(path, event):
 path=Path(path)
 if not _local(path): raise ValueError('UNSAFE_RECORD_DESTINATION')
 path.parent.mkdir(parents=True,exist_ok=True)
 payload={'record_version':1,'timestamp':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'), **_safe(event)}
 descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
 with os.fdopen(descriptor,'a',encoding='utf-8') as stream: stream.write(json.dumps(payload,sort_keys=True)+'\n')
 return payload
