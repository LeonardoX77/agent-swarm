"""Fail-closed parser for a pinned private Pi session JSONL file."""
from __future__ import annotations
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path

MAX_FILE, MAX_LINE = 8 * 1024 * 1024, 1024 * 1024
class SessionError(ValueError): pass
class UnsafeSessionPath(SessionError): pass
class MalformedSession(SessionError): pass
@dataclass(frozen=True)
class SessionResult:
    status: str
    user_entry: str | None = None
    assistant_entry: str | None = None
    text: str | None = None


def _pending(): return SessionResult('pending')
def _private(path, mode):
    try:
        item = os.stat(path, follow_symlinks=False)
        return item.st_uid == os.geteuid() and stat.S_IMODE(item.st_mode) == mode
    except OSError: return False

def _caller_components_safe(path):
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            if current.is_symlink() and current != Path('/var'): return False
        except OSError: return False
    return True

def _safe_path(path, root):
    path, root = Path(path), Path(root)
    if (not path.is_absolute() or not root.is_absolute() or '..' in path.parts or '..' in root.parts or
            path.parts[1:2] == ('Volumes',) or not _caller_components_safe(path) or not _caller_components_safe(root)):
        raise UnsafeSessionPath('UNSAFE_SESSION_PATH')
    path, root = path.resolve(strict=False), root.resolve(strict=False)
    try: path.relative_to(root)
    except ValueError: raise UnsafeSessionPath('UNSAFE_SESSION_PATH')
    if not _private(root, 0o700): raise UnsafeSessionPath('UNSAFE_SESSION_ROOT')
    return path

def _read(path):
    if not path.exists(): return None
    try:
        before = os.lstat(path)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid() or stat.S_IMODE(before.st_mode) != 0o600: raise UnsafeSessionPath('UNSAFE_SESSION_FILE')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            after = os.fstat(fd)
            if not stat.S_ISREG(after.st_mode) or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino): raise UnsafeSessionPath('UNSAFE_SESSION_FILE')
            chunks, size = [], 0
            while True:
                chunk = os.read(fd, min(65536, MAX_FILE + 1 - size))
                if not chunk: break
                chunks.append(chunk); size += len(chunk)
                if size > MAX_FILE: raise MalformedSession('SESSION_TOO_LARGE')
        finally: os.close(fd)
    except OSError as error: raise UnsafeSessionPath('UNREADABLE_SESSION') from error
    raw, objects = b''.join(chunks), []
    for index, line in enumerate(raw.splitlines(keepends=True)):
        if len(line) > MAX_LINE: raise MalformedSession('LINE_TOO_LARGE')
        if not (line.endswith(b'\n') or line.endswith(b'\r')) and index == len(raw.splitlines(keepends=True)) - 1: return None
        try: item = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as error: raise MalformedSession('MALFORMED_JSONL') from error
        if not isinstance(item, dict): raise MalformedSession('MALFORMED_JSONL')
        objects.append(item)
    return objects

def _user_text(content):
    if isinstance(content, str): return content
    if not isinstance(content, list) or not content: return None
    values = []
    for item in content:
        if not isinstance(item, dict) or item.get('type') != 'text' or not isinstance(item.get('text'), str): return None
        values.append(item['text'])
    return ''.join(values)

def _assistant_text(content):
    if not isinstance(content, list): return None
    values = []
    for item in content:
        if not isinstance(item, dict): return None
        if item.get('type') == 'thinking': continue
        if item.get('type') != 'text' or not isinstance(item.get('text'), str): return None
        values.append(item['text'])
    return ''.join(values)

def parse_session_result(session_path, session_root, expected_session_id, user_prompt):
    if not isinstance(expected_session_id, str) or not expected_session_id or not isinstance(user_prompt, str) or not user_prompt: raise SessionError('INVALID_EXPECTATION')
    objects = _read(_safe_path(session_path, session_root))
    if objects is None: return _pending()
    if not objects or objects[0].get('type') != 'session' or objects[0].get('version') != 3 or objects[0].get('id') != expected_session_id: raise MalformedSession('FOREIGN_OR_MISSING_HEADER')
    if sum(item.get('type') == 'session' for item in objects) != 1: raise MalformedSession('MULTIPLE_SESSIONS')
    entries, children = {}, {}
    for item in objects[1:]:
        identifier, parent = item.get('id'), item.get('parentId')
        if not isinstance(item.get('type'), str) or not isinstance(identifier, str) or not identifier or identifier in entries or (parent is not None and not isinstance(parent, str)): raise MalformedSession('INVALID_ENTRY')
        if item['type'] == 'message' and (not isinstance(item.get('message'), dict) or not isinstance(item['message'].get('role'), str)): raise MalformedSession('INVALID_ENTRY')
        entries[identifier] = item; children.setdefault(parent, []).append(identifier)
    for identifier, item in entries.items():
        parent = item.get('parentId')
        if parent is not None and parent not in entries: raise MalformedSession('MISSING_PARENT')
        if len(children.get(identifier, [])) > 1: raise MalformedSession('AMBIGUOUS_BRANCH')
        seen, current = set(), identifier
        while current is not None:
            if current in seen: raise MalformedSession('CYCLE')
            seen.add(current); current = entries[current].get('parentId')
    users = [key for key, item in entries.items() if item['type'] == 'message' and item['message']['role'] == 'user' and _user_text(item['message'].get('content')) == user_prompt]
    if len(users) > 1: raise MalformedSession('DUPLICATE_PROMPT')
    if not users: return _pending()
    user, ancestors, current = users[0], set(), users[0]
    while current is not None: ancestors.add(current); current = entries[current].get('parentId')
    if any(item['type'] == 'message' and item['message']['role'] == 'user' and key not in ancestors and key != user for key, item in entries.items()): raise MalformedSession('INTERFERING_USER')
    chain, current = [user], user
    while children.get(current): current = children[current][0]; chain.append(current)
    leaf = entries[chain[-1]]
    if leaf['type'] != 'message' or leaf['message']['role'] != 'assistant' or leaf['message'].get('stopReason') != 'stop': return _pending()
    text = _assistant_text(leaf['message'].get('content'))
    if not text or text == user_prompt: return _pending()
    return SessionResult('result', user, chain[-1], text)
