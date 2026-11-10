import tempfile
import unittest
from pathlib import Path
from core import Workspace
import submission


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'test.db'
        self.ws=Workspace(self.path)

    def tearDown(self):self.tmp.cleanup()

    def test_no_automatic_completion(self):
        self.assertEqual(submission.state(self.ws)['remaining'],8)
        with self.assertRaises(ValueError):submission.save(self.ws,'speech',True,'')

    def test_persists_and_can_reopen(self):
        submission.save(self.ws,'ui',True,'Reviewed locally; synthetic test observation.')
        self.assertEqual(submission.state(Workspace(self.path))['remaining'],7)
        submission.save(self.ws,'ui',False,'Needs changes')
        self.assertEqual(submission.state(self.ws)['remaining'],8)

    def test_public_demo_link_format(self):
        with self.assertRaises(ValueError):submission.save(self.ws,'demo',True,'https://example.com/demo')
        with self.assertRaises(ValueError):submission.save(self.ws,'demo',True,'https://linkedin.com.example.com/demo')
        submission.save(self.ws,'demo',True,'https://www.linkedin.com/posts/synthetic-fixture')
        self.assertEqual(submission.state(self.ws)['remaining'],7)
