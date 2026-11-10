import tempfile
import unittest
from pathlib import Path
from core import Workspace
from answers import answer


class TaskManagementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Workspace(Path(self.tmp.name) / 'test.db')
        self.sid = self.ws.source('Note', 'రవి పెన్నులు తెస్తాడు.', 'te-IN')
        self.tid = self.ws.task(self.sid, 'Bring pens', 'రవి పెన్నులు తెస్తాడు.')

    def tearDown(self):
        self.tmp.cleanup()

    def test_edit_preserves_status_and_updates_answers(self):
        self.ws.status(self.tid, 'done')
        self.ws.review_task(self.tid, 'Bring blue pens', 'రవి పెన్నులు తెస్తాడు.', 'Ravi', '2026-11-01', 1, 2)
        task = self.ws.state()['tasks'][0]
        self.assertEqual(task['status'], 'done')
        self.assertEqual(task['version'], 3)
        self.assertIn('Bring blue pens', answer(self.ws.state(), [self.sid], 'completed')['claims'][0]['text'])

    def test_stale_editor_and_delete_blocked(self):
        self.ws.status(self.tid, 'done')
        with self.assertRaises(ValueError):
            self.ws.review_task(self.tid, 'Old', 'రవి పెన్నులు తెస్తాడు.', None, None, 1, 1)
        with self.assertRaises(ValueError):
            self.ws.remove_task(self.tid, 1)

    def test_delete_preserves_source(self):
        self.ws.remove_task(self.tid, 1)
        self.assertEqual(self.ws.state()['tasks'], [])
        self.assertEqual(len(self.ws.state()['sources']), 1)

    def test_invalid_edit_rolls_back(self):
        with self.assertRaises(ValueError):
            self.ws.review_task(self.tid, 'Buy car', 'Approved car', None, None, 1, 1)
        self.assertEqual(self.ws.state()['tasks'][0]['title'], 'Bring pens')

    def test_oversized_owner_rejected_before_task_save(self):
        with self.assertRaises(ValueError):
            self.ws.task(self.sid,'Bring pens','రవి పెన్నులు తెస్తాడు.',owner='x'*161)
        self.assertEqual(len(self.ws.state()['tasks']),1)
