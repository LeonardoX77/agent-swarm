import os
import select
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "bin" / "swarm-ssh-connect"


class Server:
    def __init__(self, handler):
        self.handler = handler
    def __enter__(self):
        self.server = socket.socket(); self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("127.0.0.1", 0)); self.server.listen(); self.port = self.server.getsockname()[1]
        self.thread = threading.Thread(target=self.run); self.thread.start(); return self
    def run(self):
        connection, _ = self.server.accept()
        with connection: self.handler(connection)
    def __exit__(self, *args):
        self.server.close(); self.thread.join(timeout=2)


def read_exact(stream, expected):
    ready, _, _ = select.select([stream], [], [], 3)
    if not ready: raise AssertionError("timed out waiting for %r" % expected)
    actual = os.read(stream.fileno(), len(expected))
    if actual != expected: raise AssertionError("expected %r, got %r" % (expected, actual))


class SshConnectTests(unittest.TestCase):
    def command(self, port, *candidates, timeout="0.1"):
        return subprocess.Popen([sys.executable, str(SCRIPT), "--port", str(port), "--timeout", timeout, *candidates], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_tries_candidates_in_order_and_relays_stdio(self):
        with Server(lambda connection: connection.sendall(connection.recv(4096))) as server:
            process = self.command(server.port, "192.0.2.1", "127.0.0.1")
            process.stdin.write(b"hello\n"); process.stdin.flush(); process.stdin.close()
            self.assertEqual(process.wait(timeout=5), 0)
            output, error = process.stdout.read(), process.stderr.read()
        self.assertEqual((output, error), (b"hello\n", b""))

    def test_interactive_round_trip_does_not_wait_for_eof(self):
        def echo(connection):
            connection.sendall(connection.recv(5)); connection.sendall(connection.recv(6))
        with Server(echo) as server:
            process = self.command(server.port, "127.0.0.1")
            process.stdin.write(b"first"); process.stdin.flush(); read_exact(process.stdout, b"first")
            process.stdin.write(b"second"); process.stdin.flush(); read_exact(process.stdout, b"second")
            process.stdin.close(); self.assertEqual(process.wait(timeout=3), 0)
            self.assertEqual(process.stderr.read(), b"")

    def test_idle_longer_than_connect_timeout_still_relays(self):
        def echo(connection):
            connection.sendall(connection.recv(3)); time.sleep(.25); connection.sendall(connection.recv(3))
        with Server(echo) as server:
            process = self.command(server.port, "127.0.0.1", timeout="0.1")
            process.stdin.write(b"one"); process.stdin.flush(); read_exact(process.stdout, b"one")
            time.sleep(.2); process.stdin.write(b"two"); process.stdin.flush(); read_exact(process.stdout, b"two")
            process.stdin.close(); self.assertEqual(process.wait(timeout=3), 0)
            self.assertEqual(process.stderr.read(), b"")

    def test_remote_close_exits_cleanly_without_fatal_stdin_lock(self):
        with Server(lambda connection: connection.sendall(b"bye")) as server:
            process = self.command(server.port, "127.0.0.1")
            read_exact(process.stdout, b"bye")
            self.assertEqual(process.wait(timeout=3), 0)
            self.assertNotIn(b"Fatal Python error", process.stderr.read())

    def test_double_dash_help_candidate_is_rejected_without_usage(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--port", "22", "--", "--help"], text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 255)
        self.assertNotIn("usage:", result.stdout + result.stderr)
        self.assertIn("invalid candidate: --help", result.stderr)

    def test_all_unreachable_reports_each_candidate(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--port", "1", "--timeout", "0.1", "127.0.0.1", "127.0.0.2"], text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 255)
        self.assertIn("127.0.0.1:", result.stderr)
        self.assertIn("127.0.0.2:", result.stderr)

    def test_real_ssh_proxy_host_key_alias_accepts_right_key_and_rejects_wrong_one(self):
        if not (shutil.which("ssh") and shutil.which("ssh-keyscan")):
            self.skipTest("ssh tools unavailable")
        try:
            probe = socket.create_connection(("127.0.0.1", 22), timeout=.5)
        except OSError:
            self.skipTest("localhost sshd unavailable")
        else:
            probe.close()
        scan = subprocess.run(["ssh-keyscan", "-t", "ed25519", "127.0.0.1"], text=True, capture_output=True, timeout=5)
        if scan.returncode or not scan.stdout.strip(): self.skipTest("localhost ed25519 key unavailable")
        fields = next((line.split() for line in scan.stdout.splitlines() if len(line.split()) == 3 and line.split()[1] == "ssh-ed25519"), None)
        if fields is None: self.skipTest("localhost ed25519 key unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); known = root / "known_hosts"; config = root / "config"
            config.write_text("Host swarm-test\n  HostName 127.0.0.1\n  Port 2222\n  HostKeyAlias swarm-test\n  User nobody\n  BatchMode yes\n  PreferredAuthentications none\n  StrictHostKeyChecking yes\n  UserKnownHostsFile %s\n  ProxyCommand %s %s --port 22 127.0.0.1\n" % (known, sys.executable, SCRIPT))
            for key, expected in ((fields[2], "Permission denied"), ("AAAA", "Host key verification failed")):
                known.write_text("swarm-test %s %s\n" % (fields[1], key))
                result = subprocess.run(["ssh", "-F", str(config), "swarm-test", "true"], text=True, capture_output=True, timeout=10)
                self.assertIn(expected, result.stderr)


if __name__ == "__main__":
    unittest.main()
