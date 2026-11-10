import tempfile
import unittest
from pathlib import Path
from core import Workspace
import evaluations
import demo


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'test.db'
        self.ws=Workspace(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_results_are_untested(self):
        result=evaluations.results(self.ws)
        self.assertEqual(len(result['cases']),20)
        self.assertEqual(result['counts']['not_tested'],20)

    def test_persist_method_and_latest_observation(self):
        evaluations.record(self.ws,'tts','blocked','manual_local','No key configured.')
        evaluations.record(self.ws,'tts','passed','mocked','Mock audio playback only.')
        result=evaluations.results(Workspace(self.path))
        self.assertEqual(result['counts']['passed'],1)
        self.assertEqual(next(c for c in result['cases'] if c['case_id']=='tts')['method'],'mocked')

    def test_pass_requires_observation_and_method(self):
        with self.assertRaises(ValueError):evaluations.record(self.ws,'tts','passed','not_tested','')
        with self.assertRaises(ValueError):evaluations.record(self.ws,'unknown','passed','mocked','Test')
        self.assertEqual(evaluations.results(self.ws)['counts']['not_tested'],20)

    def test_demo_reset_clears_test_results(self):
        evaluations.record(self.ws,'tts','blocked','manual_local','No key.')
        demo.reset(self.ws,True,True)
        self.assertEqual(evaluations.results(self.ws)['counts']['not_tested'],20)
