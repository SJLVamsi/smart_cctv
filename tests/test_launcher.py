import unittest, sys, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run
from dashboard import create_app


class LauncherTests(unittest.TestCase):
    def test_bind_reports_port_in_use_clearly(self):
        app_one = create_app(tempfile.mkdtemp())
        server = run.bind(app_one, 0)          # 0 -> grab a free port
        try:
            busy_port = server.socket.getsockname()[1]
            with self.assertRaises(SystemExit) as caught:
                run.bind(create_app(tempfile.mkdtemp()), busy_port)
            message = str(caught.exception)
            self.assertIn(str(busy_port), message)
            self.assertIn('already in use', message)
        finally:
            server.server_close()


if __name__ == '__main__':
    unittest.main()
