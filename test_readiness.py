import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import readiness


class ReadinessTests(unittest.TestCase):
    @patch('providers.synthesize', side_effect=HTTPError('https://example.test', 403, 'SECRET', {}, None))
    @patch('providers.transcribe')
    def test_failure_stops_without_retry_and_hides_response(self, stt, tts):
        result = readiness.live_checks('speech')
        self.assertEqual([c['status'] for c in result], ['failed', 'not_run'])
        self.assertNotIn('SECRET', str(result))
        tts.assert_called_once()
        stt.assert_not_called()

    @patch('providers.propose', return_value={'tasks': [{'title':'Check'}]})
    @patch('summaries.generate', return_value=[{'text':'Mock','quote':'Mock'}])
    @patch('readiness.answer', side_effect=[{'abstain': False}, {'abstain': True}])
    def test_reasoning_check_sequence(self, answer, generate, propose):
        result = readiness.live_checks('reasoning')
        self.assertEqual(len(result), 5)
        self.assertTrue(all(c['status']=='passed' for c in result))
        self.assertEqual(generate.call_count, 2)

    @patch.dict('os.environ', {}, clear=True)
    def test_unconfigured_is_not_ready(self):
        self.assertEqual(readiness.configuration(), {'speech_configured':False,'reasoning_configured':False})
