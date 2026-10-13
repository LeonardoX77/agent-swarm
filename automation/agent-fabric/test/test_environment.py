import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from environment import SAFE_PATH, child_environment


class ChildEnvironmentTests(unittest.TestCase):
    def test_builds_minimal_environment_from_approved_values(self):
        source = {
            'HOME': '/Users/leo',
            'USER': 'leo',
            'LOGNAME': 'leo',
            'LANG': 'en_US.UTF-8',
            'LC_CTYPE': 'en_US.UTF-8',
            'SSH_AUTH_SOCK': '/private/tmp/agent.sock',
            'UNRELATED_SETTING': 'not-forwarded',
        }

        self.assertEqual(child_environment(source), {
            'HOME': '/Users/leo',
            'USER': 'leo',
            'LOGNAME': 'leo',
            'LANG': 'en_US.UTF-8',
            'LC_CTYPE': 'en_US.UTF-8',
            'PATH': SAFE_PATH,
        })

    def test_rejects_execution_and_config_injection_variables(self):
        for name in (
            'BASH_ENV', 'ENV', 'PYTHONPATH', 'PYTHONHOME', 'NODE_OPTIONS',
            'PI_CODING_AGENT_DIR', 'PI_CODING_AGENT_SESSION_DIR',
            'PI_PACKAGE_DIR', 'LD_PRELOAD', 'DYLD_INSERT_LIBRARIES',
        ):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, 'UNSAFE_ENVIRONMENT'):
                    child_environment({name: 'injected'})

    def test_ignores_unsafe_locale_names_or_values(self):
        self.assertEqual(child_environment({
            'LANG': 'en_US.UTF-8;evil',
            'LC_invalid': 'en_US.UTF-8',
            'LC_TIME': 'C',
        }), {'LC_TIME': 'C', 'PATH': SAFE_PATH})


if __name__ == '__main__':
    unittest.main()
