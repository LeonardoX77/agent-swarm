import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'lib'))
from pi_session_result import MAX_FILE, MAX_LINE, MalformedSession, UnsafeSessionPath, parse_session_result

PROMPT = 'Inspect focused findings.'


def message(identifier, parent, role, content, **extra):
    return {'type': 'message', 'id': identifier, 'parentId': parent, 'message': {'role': role, 'content': content, **extra}}


def write_session(path, entries):
    values = [{'type': 'session', 'version': 3, 'id': 'session-1'}, *entries]
    path.write_text('\n'.join(json.dumps(item) for item in values) + '\n', encoding='utf-8')
    path.chmod(0o600)


class PiSessionResultTests(unittest.TestCase):
    def test_actual_header_metadata_and_string_user_content_have_linked_result(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            write_session(path, [
                {'type': 'model_change', 'id': 'model', 'parentId': None, 'model': 'x'},
                {'type': 'thinking_level_change', 'id': 'thinking', 'parentId': 'model', 'level': 'high'},
                message('user', 'thinking', 'user', PROMPT),
                message('tool', 'user', 'assistant', [{'type': 'toolUse', 'id': 't', 'name': 'x', 'input': {}}]),
                {'type': 'tool_result', 'id': 'result', 'parentId': 'tool', 'toolUseId': 't'},
                message('answer', 'result', 'assistant', [{'type': 'text', 'text': 'Answer'}], stopReason='stop'),
            ])
            result = parse_session_result(path, Path(directory), 'session-1', PROMPT)
            self.assertEqual((result.status, result.user_entry, result.assistant_entry, result.text), ('result', 'user', 'answer', 'Answer'))

    def test_pi_102_long_system_prompt_on_parent_chain_has_linked_result(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            system_prompt = 's' * 99373
            write_session(path, [
                {'type': 'model_change', 'id': 'model', 'parentId': None, 'model': 'x'},
                {'type': 'thinking_level_change', 'id': 'thinking', 'parentId': 'model', 'level': 'high'},
                message('system', 'thinking', 'system', system_prompt),
                message('user', 'system', 'user', [{'type': 'text', 'text': PROMPT}]),
                message('answer', 'user', 'assistant', [{'type': 'text', 'text': 'Pi 1.0.2 answer'}], stopReason='stop'),
            ])
            result = parse_session_result(path, Path(directory), 'session-1', PROMPT)
            self.assertEqual((result.status, result.text), ('result', 'Pi 1.0.2 answer'))

    def test_system_message_is_never_a_prompt_or_result(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            write_session(path, [message('system', None, 'system', PROMPT)])
            self.assertEqual(parse_session_result(path, Path(directory), 'session-1', PROMPT).status, 'pending')

    def test_rejects_lines_and_files_above_bounded_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            write_session(path, [{'type': 'model_change', 'id': 'model', 'parentId': None, 'padding': 'x' * MAX_LINE}])
            with self.assertRaisesRegex(MalformedSession, 'LINE_TOO_LARGE'):
                parse_session_result(path, Path(directory), 'session-1', PROMPT)
            path.write_bytes(b'x' * (MAX_FILE + 1)); path.chmod(0o600)
            with self.assertRaisesRegex(MalformedSession, 'SESSION_TOO_LARGE'):
                parse_session_result(path, Path(directory), 'session-1', PROMPT)

    def test_partial_is_pending_and_complete_malformed_or_branch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text(json.dumps({'type': 'session', 'version': 3, 'id': 'session-1'}) + '\n{"type"', encoding='utf-8'); path.chmod(0o600)
            self.assertEqual(parse_session_result(path, Path(directory), 'session-1', PROMPT).status, 'pending')
            write_session(path, [message('user', None, 'user', PROMPT), message('a', 'user', 'assistant', [{'type': 'text', 'text': 'a'}], stopReason='stop'), message('b', 'user', 'assistant', [{'type': 'text', 'text': 'b'}], stopReason='stop')])
            with self.assertRaises(MalformedSession): parse_session_result(path, Path(directory), 'session-1', PROMPT)

    def test_rejects_mixed_submitted_user_content_and_tool_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            write_session(path, [message('user', None, 'user', [{'type': 'text', 'text': PROMPT}, {'type': 'toolUse', 'id': 'x'}]), message('answer', 'user', 'assistant', [{'type': 'text', 'text': 'Answer'}], stopReason='stop')])
            self.assertEqual(parse_session_result(path, Path(directory), 'session-1', PROMPT).status, 'pending')
            write_session(path, [message('user', None, 'user', PROMPT), message('answer', 'user', 'assistant', [{'type': 'toolUse', 'id': 'x'}], stopReason='stop')])
            self.assertEqual(parse_session_result(path, Path(directory), 'session-1', PROMPT).status, 'pending')

    def test_rejects_symlink_ancestor_and_non_regular_session_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); outside = root / 'outside'; outside.mkdir()
            link = root / 'link'; link.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(UnsafeSessionPath): parse_session_result(link / 'session.jsonl', root, 'session-1', PROMPT)
            fifo = root / 'pipe'; os.mkfifo(fifo, 0o600)
            with self.assertRaises(UnsafeSessionPath): parse_session_result(fifo, root, 'session-1', PROMPT)
            target = root / 'target.jsonl'; write_session(target, [])
            leaf = root / 'leaf.jsonl'; leaf.symlink_to(target)
            with self.assertRaises(UnsafeSessionPath): parse_session_result(leaf, root, 'session-1', PROMPT)


if __name__ == '__main__': unittest.main()
