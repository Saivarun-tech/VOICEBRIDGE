import tempfile
import unittest
from pathlib import Path
from core import Workspace, validate_proposal


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.sqlite3'
        self.ws = Workspace(self.path)
        self.sid = self.ws.source('Handover', 'Anita will check the projector. Room unconfirmed.', 'en-IN')

    def tearDown(self):
        self.tmp.cleanup()

    def test_review_persist_complete_report(self):
        tid = self.ws.task(self.sid, 'Check projector', 'Anita will check the projector.', 'Anita')
        restarted = Workspace(self.path)
        restarted.status(tid, 'done')
        report = restarted.report(self.sid)
        self.assertIn('[x] Check projector', report)
        self.assertIn('Due: Unspecified', report)
        self.assertEqual(restarted.search('PROJECTOR')[0]['id'], self.sid)

    def test_reject_invented_evidence_without_saving(self):
        with self.assertRaises(ValueError):
            self.ws.task(self.sid, 'Buy a projector', 'Budget approved')
        self.assertEqual(self.ws.state()['tasks'], [])

    def test_reject_model_hallucinated_quote(self):
        with self.assertRaises(ValueError):
            validate_proposal({'summary': 'Budget approved', 'tasks': [
                {'title': 'Buy', 'quote': 'Budget approved'}]}, 'Room unconfirmed.')

    def test_telugu_evidence_and_unknowns(self):
        sid = self.ws.source('తెలుగు', 'రెండు బ్లూ పెన్నులు కావాలి', 'te-IN')
        self.ws.task(sid, 'Review pen request', 'రెండు బ్లూ పెన్నులు కావాలి')
        task = self.ws.state()['tasks'][0]
        self.assertIsNone(task['owner'])
        self.assertIsNone(task['due'])
        self.assertEqual(len(self.ws.search('పెన్నులు')), 1)

    def test_reject_invalid_date_and_status(self):
        with self.assertRaises(ValueError):
            self.ws.task(self.sid, 'Check', 'Room unconfirmed.', due='tomorrow')
        with self.assertRaises(ValueError):
            self.ws.status('missing', 'done')


if __name__ == '__main__':
    unittest.main()
