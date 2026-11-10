"""One private key prompt; no secrets are saved or accepted on the command line."""
import argparse
import getpass
import os
from pathlib import Path
import runpy
import sys
import json
import re
import urllib.request
import urllib.parse
from urllib.error import HTTPError, URLError

ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/models'
DEFAULT_MODEL = 'gemini-3.1-flash-lite'


def available_models(key):
    names = set()
    token = None
    for _ in range(10):
        query = {'pageSize': 1000}
        if token:
            query['pageToken'] = token
        url = 'https://generativelanguage.googleapis.com/v1beta/models?' + urllib.parse.urlencode(query)
        req = urllib.request.Request(url, headers={'x-goog-api-key': key, 'User-Agent': 'VoiceBridge/0.1'})
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('Model list is unexpectedly large.')
        data = json.loads(raw)
        for model in data.get('models', []):
            name = model.get('name', '').removeprefix('models/')
            if 'generateContent' in model.get('supportedGenerationMethods', []) and re.fullmatch(r'gemini-[A-Za-z0-9._-]{1,120}', name):
                names.add(name)
        token = data.get('nextPageToken')
        if not token:
            return sorted(names)
    raise ValueError('Model list exceeded the page limit.')


def configure(model, key):
    if not isinstance(model, str) or not model.strip() or not isinstance(key, str) or not key.strip():
        raise ValueError('Model and Gemini key must not be blank.')
    os.environ['VOICEBRIDGE_LLM_URL'] = ENDPOINT
    os.environ['VOICEBRIDGE_LLM_MODEL'] = model.strip()
    os.environ['VOICEBRIDGE_LLM_KEY'] = key.strip()


def choose_model(names, requested=None, prompt=input):
    candidates = [name for name in names if not any(tag in name.lower() for tag in
                  ('image', 'audio', 'tts', 'live', 'robotics', 'computer-use'))]
    if requested:
        if requested not in candidates:
            raise ValueError('Requested text model was not returned by Google. Run without --model to choose an available model.')
        return requested
    if not candidates:
        raise ValueError('No matching text models returned. Check your AI Studio project access.')
    print('Text-model candidates returned by Google:')
    for number, name in enumerate(candidates, 1):
        print(f'  {number}. {name}')
    print('Listing does not guarantee free quota, pricing or chat compatibility. Choose a model enabled for your project. No automatic fallback.')
    choice = prompt('Model number (or q to stop): ').strip()
    if choice.lower() == 'q':
        raise ValueError('Stopped before generation requests.')
    if not choice.isdigit() or not 1 <= int(choice) <= len(candidates):
        raise ValueError('Invalid selection. Stopped before generation requests.')
    return candidates[int(choice)-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('models', 'check', 'demo', 'app'))
    parser.add_argument('--model', default=DEFAULT_MODEL, help='Model ID; defaults to the live-verified gemini-3.1-flash-lite. Use --choose-model for a menu.')
    parser.add_argument('--choose-model', action='store_true')
    parser.add_argument('--port', type=int, default=8775)
    parser.add_argument('--speech-key', action='store_true')
    args = parser.parse_args()
    print('Gemini setup: discover models first. Key stays in this process only.', flush=True)
    key = getpass.getpass('Gemini API key (hidden): ')
    if not key.strip():
        raise SystemExit('Key must not be blank.')
    try:
        names = available_models(key.strip())
    except HTTPError as error:
        raise SystemExit(f'Model listing HTTP {error.code}. No retry; key and response hidden.')
    except (URLError, OSError, ValueError):
        raise SystemExit('Model listing failed. No retry; key and response hidden.')
    if args.action == 'models':
        print('Models returned by Google supporting generateContent (not proof of quota or chat compatibility):')
        for name in names:
            print(name)
        if not names:
            print('No matching Gemini models returned.')
        return
    try:
        model = choose_model(names, None if args.choose_model else args.model)
        configure(model, key)
    except ValueError as error:
        raise SystemExit(str(error))
    print(f'Selected model: {model}', flush=True)
    del key
    root = Path(__file__).resolve().parent
    if args.action == 'check':
        sys.argv = ['readiness.py', '--live', '--group', 'reasoning']
        runpy.run_path(str(root / 'readiness.py'), run_name='__main__')
    else:
        sys.argv = ['app.py', '--port', str(args.port)]
        if args.action == 'demo':
            sys.argv.append('--demo')
        if args.speech_key:
            sys.argv.append('--speech-key')
        runpy.run_path(str(root / 'app.py'), run_name='__main__')


if __name__ == '__main__':
    main()
