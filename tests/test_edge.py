import unittest, sys, tempfile, threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edge import EdgeNode, mjpeg_stream


class PostTests(unittest.TestCase):
    def test_failed_post_is_non_fatal_and_counted(self):
        # Nothing is listening on port 1; a real demo must survive this.
        node = EdgeNode('assets/sample.mp4', 'http://127.0.0.1:1', pace=False)
        try:
            ok = node.post('/api/metrics', {'status': 'x'})
            self.assertFalse(ok)
            self.assertEqual(node.post_failures, 1)
        finally:
            node.session.close()

    def test_successful_post_counts_bytes(self):
        from werkzeug.serving import make_server
        from dashboard import create_app
        with tempfile.TemporaryDirectory() as t:
            server = make_server('127.0.0.1', 0, create_app(t), threaded=True)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            node = EdgeNode('assets/sample.mp4', f'http://127.0.0.1:{server.port}', pace=False)
            try:
                self.assertTrue(node.post('/api/metrics', {'status': 'x'}))
                self.assertGreater(node.sent, 0)
                self.assertEqual(node.post_failures, 0)
            finally:
                node.session.close()
                server.shutdown()


class StreamTests(unittest.TestCase):
    def test_multipart_stream_frames_latest_jpeg(self):
        frames = iter([b'AAA', b'BBB'])
        stop = threading.Event()
        stream = mjpeg_stream(lambda: next(frames, None), stop)
        first = next(stream)
        second = next(stream)
        self.assertTrue(first.startswith(b'--edgeframe\r\n'))
        self.assertIn(b'Content-Type: image/jpeg', first)
        self.assertIn(b'AAA', first)
        self.assertTrue(second.endswith(b'BBB\r\n'))


class EdgeAppTests(unittest.TestCase):
    def test_monitor_page_renders_stream_and_legend(self):
        node = EdgeNode('assets/sample.mp4', 'http://127.0.0.1:1', pace=False)
        try:
            html = node.app.test_client().get('/').get_data(as_text=True)
            self.assertIn('Local edge monitor', html)
            self.assertIn('/stream.mjpg', html)
        finally:
            node.session.close()

    def test_health_exposes_failures_and_stats(self):
        node = EdgeNode('assets/sample.mp4', 'http://127.0.0.1:1', pace=False)
        try:
            body = node.app.test_client().get('/api/health').get_json()
            self.assertEqual(body['post_failures'], 0)
            self.assertEqual(body['stats'], {})
        finally:
            node.session.close()


class ReplayTests(unittest.TestCase):
    def test_request_replay_rejected_until_complete(self):
        node = EdgeNode('assets/sample.mp4', 'http://127.0.0.1:1', pace=False)
        try:
            self.assertFalse(node.request_replay())
            node.done = True
            self.assertTrue(node.request_replay())
            self.assertTrue(node.replay.is_set())
        finally:
            node.session.close()

    def test_replay_endpoint_status_codes(self):
        node = EdgeNode('assets/sample.mp4', 'http://127.0.0.1:1', pace=False)
        try:
            client = node.app.test_client()
            self.assertEqual(client.post('/api/replay').status_code, 409)
            node.done = True
            self.assertEqual(client.post('/api/replay').status_code, 202)
        finally:
            node.session.close()


if __name__ == '__main__':
    unittest.main()
