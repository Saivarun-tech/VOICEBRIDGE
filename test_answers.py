import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core import Workspace
from answers import answer, validate_answer, fingerprint


class AnswerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Workspace(Path(self.tmp.name) / 'test.db')
        self.sid = self.ws.source('తెలుగు note', 'రవి పెన్నులు తెస్తాడు. Room booking unconfirmed.', 'te-IN')
        self.tid = self.ws.task(self.sid, 'Bring pens', 'రవి పెన్నులు తెస్తాడు.')

    def tearDown(self):
        self.tmp.cleanup()

    def test_pending_completed_without_provider(self):
        with patch('providers.reason_json') as model:
            self.assertEqual(len(answer(self.ws.state(), [self.sid], 'pending')['claims']), 1)
            self.ws.status(self.tid, 'done')
            self.assertEqual(len(answer(self.ws.state(), [self.sid], 'completed')['claims']), 1)
            self.assertEqual(answer(self.ws.state(), [self.sid], 'pending')['claims'], [])
            model.assert_not_called()

    def test_correction_excludes_stale_tasks_and_changes_fingerprint(self):
        before = fingerprint(self.ws.state(), [self.sid])
        self.ws.correct(self.sid, 'Corrected', 'Cancel pens.', 'en-IN', 1)
        result = answer(self.ws.state(), [self.sid], 'pending')
        self.assertEqual(result['claims'], [])
        self.assertIn('1 task(s) excluded', result['message'])
        self.assertNotEqual(before, fingerprint(self.ws.state(), [self.sid]))

    def test_evidence_validation_and_abstention(self):
        sources = self.ws.state()['sources']
        raw = {'abstain': False, 'claims': [{'text': 'Room booking is unconfirmed.',
                'citations': [{'source_id': self.sid, 'quote': 'Room booking unconfirmed.'}]}]}
        self.assertEqual(validate_answer(raw, sources)['claims'][0]['citations'][0]['revision'], 1)
        raw['claims'][0]['citations'][0]['quote'] = 'Room confirmed.'
        with self.assertRaises(ValueError):
            validate_answer(raw, sources)
        self.assertTrue(validate_answer({'abstain': True}, sources)['abstain'])
        with self.assertRaises(ValueError):
            validate_answer({'abstain': False, 'claims': [{'text': 'Yes', 'citations': []}]}, sources)

    @patch('providers.reason_json', return_value={'abstain': True, 'claims': []})
    def test_ai_abstains_and_passes_question_as_data(self, model):
        result = answer(self.ws.state(), [self.sid], 'question', 'బడ్జెట్ ఎంత?')
        self.assertTrue(result['abstain'])
        self.assertEqual(model.call_args.args[1]['question'], 'బడ్జెట్ ఎంత?')

    def test_deleted_source_and_scope_limits(self):
        self.ws.delete(self.sid, 1)
        for ids in ([self.sid], [], ['x']*7):
            with self.assertRaises(ValueError):
                answer(self.ws.state(), ids, 'pending')
