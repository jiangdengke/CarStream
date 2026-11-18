import fcntl
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_SERVER = """\
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

print('fixture stdout', flush=True)
print('fixture stderr', file=sys.stderr, flush=True)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'fixture alive')

HTTPServer(('127.0.0.1', int(os.environ['CARSTREAM_PORT'])), HealthHandler).serve_forever()
"""


@unittest.skipUnless(
    sys.platform == "linux" and shutil.which("ss") and shutil.which("flock"),
    "Lifecycle checks require Linux, ss and flock",
)
class LifecycleScriptTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory(prefix="carstream script check ")
        self.addCleanup(self.temporary_directory.cleanup)
        self.project = Path(self.temporary_directory.name)
        (self.project / ".venv/bin").mkdir(parents=True)
        (self.project / "carstream").mkdir()
        for script_name in ("start.sh", "stop.sh"):
            shutil.copy2(PROJECT_ROOT / script_name, self.project / script_name)
        (self.project / ".venv/bin/python").symlink_to(sys.executable)
        (self.project / "carstream/__init__.py").touch()
        shutil.copy2(PROJECT_ROOT / "carstream/config.py", self.project / "carstream")
        (self.project / "carstream/__main__.py").write_text(FIXTURE_SERVER)
        self.port_reservation = socket.socket()
        self.addCleanup(self.port_reservation.close)
        self.port_reservation.bind(("127.0.0.1", 0))
        self.port = self.port_reservation.getsockname()[1]
        (self.project / ".env").write_text(
            "CARSTREAM_ACCESS_TOKEN='lifecycle-test-token-not-a-real-secret'\n"
            f"CARSTREAM_PORT='{self.port}'\n"
        )
        self.addCleanup(self.stop_fixture)

    def run_script(self, script_name):
        environment = {
            name: value for name, value in os.environ.items() if not name.startswith("CARSTREAM_")
        }
        if script_name == "start.sh":
            self.port_reservation.close()
        return subprocess.run(
            [str(self.project / script_name)],
            cwd="/",
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def stop_fixture(self):
        pid_file = self.project / "server.pid"
        if pid_file.exists() and pid_file.read_text().strip().isdigit():
            process_id = int(pid_file.read_text().strip())
            process_directory = Path(f"/proc/{process_id}/cwd")
            try:
                if process_directory.resolve(strict=True) == self.project:
                    os.kill(process_id, signal.SIGTERM)
            except (FileNotFoundError, ProcessLookupError):
                pass

    def test_background_start_repeat_start_and_stop_without_environment(self):
        result = self.run_script("start.sh")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        pid_file = self.project / "server.pid"
        process_id = pid_file.read_text()
        with urlopen(f"http://127.0.0.1:{self.port}/healthz", timeout=2) as response:
            self.assertEqual(response.read(), b"fixture alive")
        self.assertEqual(pid_file.stat().st_mode & 0o777, 0o600)
        log_directory = self.project / "log"
        log_files = list(log_directory.glob("*.log"))
        self.assertEqual(len(log_files), 1)
        self.assertRegex(log_files[0].name, r"^carstream-\d{8}T\d{6}\.\d{9}Z\.log$")
        self.assertEqual(log_directory.stat().st_mode & 0o777, 0o700)
        self.assertEqual(log_files[0].stat().st_mode & 0o777, 0o600)
        self.assertIn(str(log_files[0]), result.stdout)
        self.assertIn("fixture stdout", log_files[0].read_text())
        self.assertIn("fixture stderr", log_files[0].read_text())
        self.assertFalse((self.project / "server.log").exists())
        result = self.run_script("start.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already running", result.stdout)
        self.assertEqual(pid_file.read_text(), process_id)
        self.assertEqual(list(log_directory.glob("*.log")), log_files)
        (self.project / ".env").unlink()
        result = self.run_script("stop.sh")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(pid_file.exists())
        self.assertEqual(self.run_script("stop.sh").returncode, 0)
        with socket.socket() as connection:
            self.assertNotEqual(connection.connect_ex(("127.0.0.1", self.port)), 0)

    def test_restart_creates_a_new_log_and_preserves_previous_output(self):
        result = self.run_script("start.sh")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.run_script("stop.sh").returncode, 0)
        previous_log = next((self.project / "log").glob("*.log"))
        previous_output = previous_log.read_bytes()
        result = self.run_script("start.sh")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        log_files = list((self.project / "log").glob("*.log"))
        self.assertEqual(len(log_files), 2)
        self.assertEqual(previous_log.read_bytes(), previous_output)
        current_log = next(log_file for log_file in log_files if log_file != previous_log)
        self.assertIn(str(current_log), result.stdout)
        self.assertIn("fixture stdout", current_log.read_text())
        self.assertEqual(self.run_script("stop.sh").returncode, 0)

    def test_unrelated_process_in_same_directory_is_not_replaced_or_stopped(self):
        unrelated_process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"], cwd=self.project
        )
        try:
            (self.project / "server.pid").write_text(f"{unrelated_process.pid}\n")
            for script_name in ("start.sh", "stop.sh"):
                result = self.run_script(script_name)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("another process", result.stderr)
                self.assertIsNone(unrelated_process.poll())
        finally:
            unrelated_process.terminate()
            unrelated_process.wait(timeout=5)

    def test_invalid_process_ids_are_refused(self):
        for process_id in ("0", "-1", "invalid", ""):
            with self.subTest(process_id=process_id):
                (self.project / "server.pid").write_text(process_id + "\n")
                for script_name in ("start.sh", "stop.sh"):
                    result = self.run_script(script_name)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("Invalid server.pid", result.stderr)

    def test_stale_pid_can_be_removed_and_replaced(self):
        completed_process = subprocess.Popen(["true"])
        completed_process.wait()
        pid_file = self.project / "server.pid"
        pid_file.write_text(f"{completed_process.pid}\n")
        self.assertEqual(self.run_script("stop.sh").returncode, 0)
        self.assertFalse(pid_file.exists())
        pid_file.write_text(f"{completed_process.pid}\n")
        result = self.run_script("start.sh")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotEqual(int(pid_file.read_text()), completed_process.pid)
        self.assertEqual(self.run_script("stop.sh").returncode, 0)

    def test_occupied_port_is_not_mistaken_for_successful_startup(self):
        self.port_reservation.close()
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", self.port))
            listener.listen()
            result = self.run_script("start.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already listening", result.stderr)
        self.assertFalse((self.project / "server.pid").exists())

    def test_startup_failure_does_not_leave_a_successful_pid_record(self):
        (self.project / "carstream/__main__.py").write_text("raise SystemExit(7)\n")
        result = self.run_script("start.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Startup failed", result.stderr)
        self.assertFalse((self.project / "server.pid").exists())
        failure_log = next((self.project / "log").glob("*.log"))
        self.assertIn(str(failure_log), result.stderr)

    def test_lifecycle_lock_refuses_overlapping_operations(self):
        with (self.project / "server.lock").open("w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            for script_name in ("start.sh", "stop.sh"):
                result = self.run_script(script_name)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Another start/stop operation", result.stderr)
