import json
import os
import unittest
from unittest.mock import patch
import gemini_setup
import providers
import io


class GeminiSetupTests(unittest.TestCase):
    def test_safe_google_error_does_not_echo_provider_message(self):
        result=providers.google_error_category(json.dumps({'error':{'status':'NOT_FOUND',
            'message':'Model not found; secret-key-should-not-be-printed'}}).encode())
        self.assertIn('NOT_FOUND',result)
        self.assertNotIn('secret-key',result)
        self.assertIn('Requested model/resource not found',result)
    def test_choose_available_text_model_without_guessing(self):
        names=['gemini-test-image','gemini-new-flash']
        self.assertEqual(gemini_setup.choose_model(names,prompt=lambda _: '1'),'gemini-new-flash')
        with self.assertRaises(ValueError):
            gemini_setup.choose_model(names,'gemini-unavailable')
        with self.assertRaises(ValueError):
            gemini_setup.choose_model(names,prompt=lambda _: 'q')

    @patch('gemini_setup.available_models', return_value=['gemini-new-flash'])
    @patch('gemini_setup.choose_model', return_value='gemini-new-flash')
    @patch('getpass.getpass', return_value='synthetic-test-key')
    @patch('runpy.run_path')
    @patch.dict(os.environ, {}, clear=True)
    def test_check_uses_discovered_choice(self, run, getpass, choose, discover):
        with patch('sys.argv',['gemini_setup.py','check']):
            gemini_setup.main()
        self.assertEqual(os.environ['VOICEBRIDGE_LLM_MODEL'],'gemini-new-flash')
        discover.assert_called_once_with('synthetic-test-key')
        run.assert_called_once()
    @patch('urllib.request.urlopen')
    def test_lists_supported_models_only(self, open_url):
        raw=json.dumps({'models':[
            {'name':'models/gemini-test-flash','supportedGenerationMethods':['generateContent']},
            {'name':'models/embedding-only','supportedGenerationMethods':['embedContent']}
        ]}).encode()
        open_url.return_value.__enter__.return_value=io.BytesIO(raw)
        self.assertEqual(gemini_setup.available_models('synthetic-key'),['gemini-test-flash'])
        self.assertNotIn('synthetic-key',open_url.call_args.args[0].full_url)
    @patch.dict(os.environ, {}, clear=True)
    def test_preset_without_file_storage(self):
        gemini_setup.configure('gemini-2.5-flash-lite','synthetic-test-key')
        self.assertEqual(os.environ['VOICEBRIDGE_LLM_URL'],gemini_setup.ENDPOINT)
        self.assertEqual(os.environ['VOICEBRIDGE_LLM_MODEL'],'gemini-2.5-flash-lite')

    @patch.dict(os.environ, {}, clear=True)
    @patch('providers.request',return_value=b'{"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":"{\\"ok\\":true}"}]}}]}')
    def test_gemini_json_contract(self, request):
        gemini_setup.configure(gemini_setup.DEFAULT_MODEL,'synthetic-test-key')
        self.assertTrue(providers.reason_json('Return JSON',{'test':True})['ok'])
        body=json.loads(request.call_args.args[1])
        self.assertEqual(body['generationConfig']['responseMimeType'],'application/json')
        self.assertNotIn('thinkingConfig',body['generationConfig'])
        self.assertTrue(request.call_args.args[0].endswith('/gemini-3.1-flash-lite:generateContent'))
        self.assertIn('x-goog-api-key',request.call_args.args[2])

    @patch('providers.request',return_value=b'{"candidates":[{"finishReason":"MAX_TOKENS","content":{"parts":[{"text":"{}"}]}}]}')
    def test_native_incomplete_response_rejected(self, request):
        with self.assertRaises(ValueError):
            providers.gemini_json('gemini-2.5-flash-lite','synthetic','JSON',{},100)

    def test_blank_key_rejected(self):
        with self.assertRaises(ValueError):gemini_setup.configure(gemini_setup.DEFAULT_MODEL,' ')
