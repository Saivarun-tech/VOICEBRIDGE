import tempfile
import unittest
from pathlib import Path
from core import Workspace
import demo


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.main = Workspace(Path(self.tmp.name)/'main.db')
        self.sandbox = Workspace(Path(self.tmp.name)/'demo.db')
        self.sid = self.main.source('Private main note', 'Keep this record.', 'en-IN')

    def tearDown(self):
        self.tmp.cleanup()

    def test_seed_idempotent_and_has_no_fake_ai_outputs(self):
        self.assertEqual(demo.seed(self.sandbox),3)
        self.assertEqual(demo.seed(self.sandbox),0)
        self.assertEqual(self.sandbox.state()['tasks'],[])
        self.assertEqual(len(self.main.state()['sources']),1)

    def test_reset_isolated_and_requires_confirmation(self):
        demo.seed(self.sandbox)
        self.sandbox.source('Practice', 'Test recording', 'en-IN')
        with self.assertRaises(ValueError): demo.reset(self.sandbox,False,True)
        with self.assertRaises(ValueError): demo.reset(self.sandbox,True,False)
        self.assertEqual(len(self.sandbox.state()['sources']),4)
        demo.reset(self.sandbox,True,True)
        self.assertEqual(len(self.sandbox.state()['sources']),3)
        self.assertEqual(self.main.state()['sources'][0]['id'],self.sid)
