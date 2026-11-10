"""Offline checks by default. Live synthetic checks require --live explicitly."""
import argparse
from datetime import datetime, timezone
import getpass
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError
import wave
import providers
import summaries
from answers import answer

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / 'local_data' / 'readiness.json'
TEXT = 'Ravi will check the projector. The room booking is not confirmed.'


def configuration():
    return {'speech_configured': bool(os.getenv('GNANI_API_KEY')),
            'reasoning_configured': all(os.getenv(k) for k in (
                'VOICEBRIDGE_LLM_URL', 'VOICEBRIDGE_LLM_KEY', 'VOICEBRIDGE_LLM_MODEL'))}


def latest():
    try:
        report = json.loads(REPORT.read_text(encoding='utf-8'))
        # Only expose the known report fields, never arbitrary local file contents.
        return {key: report.get(key) for key in ('checked_at', 'mode', 'checks', 'completed', 'limitation')}
    except (OSError, ValueError):
        return None


def failure(error):
    if isinstance(error, HTTPError):
        diagnostic = getattr(error, 'provider_diagnostic', None)
        if diagnostic:
            return f'Provider HTTP {error.code}; {diagnostic}. No retry.'
        if error.code == 404:
            return 'Provider HTTP 404; model or endpoint not found. List available models and verify the model ID. No retry.'
        return f'Provider HTTP {error.code}; check access and credits. No retry.'
    return f'{type(error).__name__}; response hidden. Check provider configuration, network or response format. No retry.'


def live_checks(group):
    source = {'id': 'synthetic-check', 'title': 'Synthetic readiness note',
              'transcript': TEXT, 'revision': 1, 'language': 'en-IN'}
    state = {'sources': [source], 'tasks': []}
    audio = {}

    def tts():
        audio['wav'] = providers.synthesize(TEXT, 'en-IN')
        with wave.open(io.BytesIO(audio['wav'])) as wav:
            duration = wav.getnframes() / wav.getframerate()
            if not 0 < duration <= 30:
                raise ValueError('Generated speech is outside the transcription limit.')

    def stt():
        transcript = providers.transcribe(audio['wav'], 'en-IN')
        if 'projector' not in transcript.casefold():
            raise ValueError('Synthetic roundtrip did not retain expected keyword.')

    def proposal():
        result = providers.propose(TEXT)
        if not result['tasks']:
            raise ValueError('Expected explicit task was not extracted.')

    def grounded():
        result = answer(state, [source['id']], 'question', 'Is the room booking confirmed?')
        if result['abstain']:
            raise ValueError('Expected source-backed answer was not produced.')

    def abstention():
        result = answer(state, [source['id']], 'question', 'What is the approved budget amount?')
        if not result['abstain']:
            raise ValueError('Model did not abstain on an unsupported question.')

    checks = []
    if group in ('all', 'speech'):
        checks += [('Gnani TTS', tts), ('Gnani STT roundtrip', stt)]
    if group in ('all', 'reasoning'):
        checks += [('Task proposal', proposal),
                   ('Telugu summary schema/evidence', lambda: summaries.generate(source, 'summary', 'te-IN')),
                   ('Hindi translation schema/evidence', lambda: summaries.generate(source, 'translation', 'hi-IN')),
                   ('Source-backed question', grounded), ('Unsupported-question abstention', abstention)]
    results = []
    for name, job in checks:
        print(f'Checking: {name}...', flush=True)
        started = time.monotonic()
        try:
            job()
            results.append({'name': name, 'status': 'passed', 'seconds': round(time.monotonic()-started, 2)})
            print(f'Passed: {name}', flush=True)
        except Exception as error:
            results.append({'name': name, 'status': 'failed', 'detail': failure(error)})
            print('Failure detail: ' + results[-1]['detail'], flush=True)
            results += [{'name': remaining, 'status': 'not_run'} for remaining, _ in checks[len(results):]]
            break
    return results


def offline_check():
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(ROOT), '-v'],
                            cwd=ROOT, capture_output=True, text=True, timeout=120)
    return [{'name': 'Offline regression suite', 'status': 'passed' if result.returncode == 0 else 'failed',
             'detail': 'No provider requests made. Run unittest -v for individual results.'}]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Makes paid synthetic provider requests; no retries.')
    parser.add_argument('--group', choices=('all', 'speech', 'reasoning'), default='all')
    args = parser.parse_args()
    if args.live:
        print('Synthetic live check: up to 2 speech + 5 reasoning calls (depending on group). Costs depend on your providers. Stops on first failure. No retries.')
        if args.group in ('all', 'speech') and not os.getenv('GNANI_API_KEY'):
            os.environ['GNANI_API_KEY'] = getpass.getpass('Gnani key (hidden, memory only): ')
        if args.group in ('all', 'reasoning'):
            for variable, label in [('VOICEBRIDGE_LLM_URL', 'Reasoning HTTPS chat-completions URL'),
                                    ('VOICEBRIDGE_LLM_MODEL', 'Reasoning model ID')]:
                if not os.getenv(variable):
                    os.environ[variable] = input(label + ': ').strip()
            if not os.getenv('VOICEBRIDGE_LLM_KEY'):
                os.environ['VOICEBRIDGE_LLM_KEY'] = getpass.getpass('Reasoning key (hidden, memory only): ')
        checks = live_checks(args.group)
    else:
        checks = offline_check()
    report = {'checked_at': datetime.now(timezone.utc).isoformat(),
              'mode': f'live_{args.group}' if args.live else 'offline', 'checks': checks,
              'completed': all(c['status'] == 'passed' for c in checks),
              'limitation': 'Smoke checks only. Passing does not verify translation meaning, summary accuracy, real microphone/noise quality, costs, or submission readiness.'}
    REPORT.parent.mkdir(exist_ok=True)
    temp = REPORT.with_suffix('.tmp')
    temp.write_text(json.dumps(report, indent=2), encoding='utf-8')
    temp.replace(REPORT)
    for check in checks:
        print(f"{check['status'].upper()}: {check['name']}")
    print('Report saved:', REPORT)
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
