import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core import Workspace
import summaries


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.db'
        self.ws = Workspace(self.path)
        self.sid = self.ws.source('Note', 'రెండు పెన్నులు కావాలి. No approval yet.', 'te-IN')
        self.passages = [{'text': 'Two pens are requested.', 'quote': 'రెండు పెన్నులు కావాలి.'}]

    def tearDown(self):
        self.tmp.cleanup()

    def test_review_persistence_and_readback_language(self):
        summaries.save(self.ws, self.sid, 1, 'summary', 'en-IN', self.passages)
        row = summaries.saved(Workspace(self.path), self.sid)[0]
        self.assertEqual(row['passages'], self.passages)
        self.assertEqual(row['language'], 'en-IN')

    def test_correction_clears_outputs_and_blocks_stale_save(self):
        summaries.save(self.ws, self.sid, 1, 'summary', 'en-IN', self.passages)
        self.ws.correct(self.sid, 'New', 'No pens needed.', 'en-IN', 1)
        self.assertEqual(summaries.saved(self.ws, self.sid), [])
        with self.assertRaises(ValueError):
            summaries.save(self.ws, self.sid, 1, 'summary', 'en-IN', self.passages)

    def test_delete_cascades_reviewed_notes(self):
        summaries.save(self.ws, self.sid, 1, 'summary', 'en-IN', self.passages)
        self.ws.delete(self.sid, 1)
        self.assertEqual(summaries.saved(self.ws, self.sid), [])

    def test_invalid_evidence_and_language(self):
        with self.assertRaises(ValueError):
            summaries.save(self.ws, self.sid, 1, 'summary', 'en-IN', [{'text':'Approved','quote':'Approved'}])
        with self.assertRaises(ValueError):
            summaries.save(self.ws, self.sid, 1, 'summary', 'xx', self.passages)

    @patch('providers.reason_json')
    def test_generate_languages_and_translation_limit(self, model):
        model.return_value = {'passages': self.passages}
        source = self.ws.state()['sources'][0]
        summaries.generate(source, 'summary', 'te-IN')
        self.assertIn('Telugu', model.call_args.args[0])
        self.assertEqual(model.call_args.kwargs['max_tokens'], 4000)
        source['transcript'] = 'x' * 4001
        model.reset_mock()
        with self.assertRaises(ValueError):
            summaries.generate(source, 'translation', 'en-IN')
        model.assert_not_called()
