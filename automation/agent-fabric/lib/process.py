"""Shell-free child process execution with deliberately minimal results."""
import subprocess

MAX_OUTPUT_BYTES = 65536


def bounded_output(value):
    """Return at most MAX_OUTPUT_BYTES of UTF-8 stdout, never stderr."""
    if not isinstance(value, str):
        return ''
    encoded = value.encode('utf-8', errors='replace')[:MAX_OUTPUT_BYTES]
    return encoded.decode('utf-8', errors='ignore')


def run(argv, *, input=None, cwd=None, timeout=None, env=None):
    try:
        return subprocess.run(argv, input=input, text=True, capture_output=True, cwd=cwd, timeout=timeout, env=env, check=False)
    except subprocess.TimeoutExpired:
        return None


def result(completed):
    if completed is None:
        return {'status': 'cancelled', 'diagnostic_code': 'TIMEOUT'}
    if completed.returncode:
        return {'status': 'failed', 'diagnostic_code': 'CHILD_FAILED', 'exit_code': completed.returncode}
    return {'status': 'succeeded', 'output': bounded_output(completed.stdout)}
