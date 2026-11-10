import tempfile
import unittest
from pathlib import Path
from core import Workspace


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.sqlite3'
        self.ws = Workspace(self.path)
        self.sid = self.ws.source('Handover', 'Anita will check the projector. Room unconfirmed.', 'en-IN')

    def tearDown(self):
        self.tmp.cleanup()

    def test_correction_invalidates_even_matching_quotes(self):
        tid = self.ws.task(self.sid, 'Check projector', 'Anita will check the projector.', revision=1)
        self.ws.correct(self.sid, 'Corrected', 'Anita will check the projector. Actually, cancel that.', 'en-IN', 1)
        with self.assertRaises(ValueError):
            self.ws.status(tid, 'done')
        with self.assertRaises(ValueError):
            self.ws.task(self.sid, 'Old proposal', 'Anita will check the projector.', revision=1)
        self.assertIn('NEEDS REVIEW', self.ws.report(self.sid))
        self.ws.review_task(tid, 'Review cancellation', 'Actually, cancel that.', None, None, 2)
        self.ws.status(tid, 'done')
        self.assertEqual(self.ws.state()['tasks'][0]['source_revision'], 2)

    def test_concurrent_edit_delete_and_cascade(self):
        self.ws.task(self.sid, 'Check', 'Room unconfirmed.')
        self.ws.correct(self.sid, 'New', 'Changed text', 'en-IN', 1)
        with self.assertRaises(ValueError):
            self.ws.correct(self.sid, 'Stale', 'Old text', 'en-IN', 1)
        with self.assertRaises(ValueError):
            self.ws.delete(self.sid, 1)
        self.ws.delete(self.sid, 2)
        self.assertEqual(self.ws.state(), {'sources': [], 'tasks': []})

    def test_invalid_correction_rolls_back(self):
        with self.assertRaises(ValueError):
            self.ws.correct(self.sid, 'Title', '', 'en-IN', 1)
        self.assertEqual(self.ws.state()['sources'][0]['revision'], 1)

    def test_migration_repeat_keeps_records(self):
        from core import Workspace
        self.assertEqual(Workspace(self.path).state()['sources'][0]['revision'], 1)
