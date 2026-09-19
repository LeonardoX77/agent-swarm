"""Pure validation and construction for restricted SSH authorized_keys entries."""
import re
from pathlib import Path

_PUBLIC_KEY = re.compile(r'^(?:ssh-(?:ed25519|rsa)|ecdsa-sha2-nistp(?:256|384|521)) [A-Za-z0-9+/]+={0,3}(?: [^\r\n]*)?$')


def _absolute_path(value):
    if not isinstance(value, str) or not Path(value).is_absolute() or any(character.isspace() or character in '"\\' for character in value):
        raise ValueError('INVALID_FORCED_COMMAND_PATH')
    return value


def authorized_keys_line(runner_path, config_path, public_key):
    """Build an exact `restrict,command=...` entry without installing it."""
    runner_path = _absolute_path(runner_path)
    config_path = _absolute_path(config_path)
    if not isinstance(public_key, str) or not _PUBLIC_KEY.fullmatch(public_key):
        raise ValueError('INVALID_PUBLIC_KEY')
    return f'restrict,command="{runner_path} --config {config_path}" {public_key}'


def validate_authorized_keys_line(line):
    if not isinstance(line, str):
        return False
    match = re.fullmatch(r'restrict,command="([^"\\ ]+) --config ([^"\\ ]+)" (.+)', line)
    if not match:
        return False
    try:
        return line == authorized_keys_line(match.group(1), match.group(2), match.group(3))
    except ValueError:
        return False
