"""Build the fixed, minimal environment used for Pi child processes."""
import re

SAFE_PATH = '/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin'
IDENTITY_VARIABLES = ('HOME', 'USER', 'LOGNAME')
LOCALE_NAME = re.compile(r'^(?:LANG|LANGUAGE|LC_[A-Z_]+)$')
LOCALE_VALUE = re.compile(r'^[A-Za-z0-9_.@-]+$')
REJECTED_VARIABLES = {
    'BASH_ENV',
    'ENV',
    'PYTHONPATH',
    'PYTHONHOME',
    'NODE_OPTIONS',
    'PI_CODING_AGENT_DIR',
    'PI_CODING_AGENT_SESSION_DIR',
    'PI_PACKAGE_DIR',
}


def child_environment(source):
    """Return approved values only, rejecting executable-runtime injection."""
    for name in source:
        if name in REJECTED_VARIABLES or name.startswith(('LD_', 'DYLD_')):
            raise ValueError('UNSAFE_ENVIRONMENT')

    environment = {'PATH': SAFE_PATH}
    for name in IDENTITY_VARIABLES:
        value = source.get(name)
        if isinstance(value, str):
            environment[name] = value
    for name, value in source.items():
        if LOCALE_NAME.fullmatch(name) and isinstance(value, str) and LOCALE_VALUE.fullmatch(value):
            environment[name] = value
    return environment
