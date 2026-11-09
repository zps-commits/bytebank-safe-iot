import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from server import app as safe_app

class TestSafeAPI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Path(self.tmp.name) / 'events.jsonl'
        self.patcher = patch.object(safe_app, 'STORE', self.store)
        self.patcher.start()
    def tearDown(self):
        self.patcher.stop()
        self.tmp.cleanup()
    def test_empty_events(self):
        self.assertEqual(safe_app.events_list()['count'], 0)
    def test_receive_and_deduplicate(self):
        body = {'event_id':'safe-01-1','device_id':'safe-01','type':'deposit_detected','pending_count':1,'lote_id':'lote-1'}
        self.assertEqual(safe_app.process_event(body)[0], 201)
        self.assertEqual(safe_app.process_event(body)[0], 200)
        self.assertEqual(safe_app.events_list()['count'], 1)
    def test_invalid_type(self):
        self.assertEqual(safe_app.process_event({'event_id':'x','device_id':'z','type':'invalid','pending_count':0})[0], 422)
    def test_invalid_payload(self):
        self.assertEqual(safe_app.process_event(None)[0], 400)
        self.assertEqual(safe_app.process_event({'event_id':'x','device_id':'z','type':'deposit_detected','pending_count':False})[0], 422)

if __name__ == '__main__':
    unittest.main()
