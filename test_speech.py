import io
import json
import os
import struct
import unittest
import wave
from unittest.mock import patch
import providers


def audio():
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b'\0\0' * 16000)
    return output.getvalue()


class SpeechTests(unittest.TestCase):
    def test_repair_streamed_header(self):
        data = bytearray(audio())
        struct.pack_into('<I', data, 40, 0xfffffffe)
        result = providers.normalize_wav(bytes(data))
        with wave.open(io.BytesIO(result)) as wav:
            self.assertEqual(wav.getnframes(), 16000)
            self.assertEqual(len(wav.readframes(16000)), 32000)

    def test_reject_non_audio(self):
        with self.assertRaises(ValueError):
            providers.normalize_wav(b'{"error":"no audio"}')

    @patch.dict(os.environ, {'GNANI_API_KEY': 'test-only'})
    @patch('providers.request', return_value=audio())
    def test_tts_payload_and_wav(self, request):
        result = providers.synthesize('నమస్కారం', 'te-IN')
        body = json.loads(request.call_args.args[1])
        self.assertEqual(body['language'], 'te-IN')
        self.assertEqual(body['voice'], 'Nalini')
        self.assertEqual(result[:4], b'RIFF')

    @patch.dict(os.environ, {'GNANI_API_KEY': 'test-only'})
    @patch('providers.request')
    def test_limits_prevent_paid_call(self, request):
        for text in ('', 'a'*801):
            with self.assertRaises(ValueError):
                providers.synthesize(text, 'auto')
        request.assert_not_called()

    @patch.dict(os.environ, {'GNANI_API_KEY': 'test-only'})
    @patch('providers.request', return_value=b'{"transcript":"hello"}')
    def test_recording_upload_contract(self, request):
        self.assertEqual(providers.transcribe(audio(), 'te-IN'), 'hello')
        self.assertIn(b'name="audio_file"', request.call_args.args[1])


if __name__ == '__main__':
    unittest.main()
