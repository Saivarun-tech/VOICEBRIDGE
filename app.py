import argparse
import base64
import getpass
import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from core import Workspace
import providers
from reporting import TEMPLATES, build_report
from answers import answer, fingerprint
import summaries
import readiness
import backups
import demo
import evaluations
import submission

ROOT = Path(__file__).resolve().parent


def handler_for(store, port, demo_mode=False):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log transcripts, secrets or request bodies.

        def send(self, status, data, kind='application/json; charset=utf-8'):
            body = json.dumps(data, ensure_ascii=False).encode() if kind.startswith('application/json') else data
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; media-src 'self' blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; object-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def allowed(self):
            return self.headers.get('Host') in (f'127.0.0.1:{port}', f'localhost:{port}')

        def do_GET(self):
            self.path = urlsplit(self.path).path
            if not self.allowed():
                return self.send(403, {'error': 'Local access only.'})
            if self.path == '/':
                return self.send(200, (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')
            if self.path == '/workflow.css':
                return self.send(200, (ROOT / 'workflow.css').read_bytes(), 'text/css; charset=utf-8')
            if self.path in ('/voice.js', '/lifecycle.js', '/reports.js', '/ask.js', '/summaries.js', '/readiness.js', '/tasks.js', '/backups.js', '/demo.js', '/evaluations.js', '/submission.js', '/workflow.js', '/recording-feedback.js', '/release-polish.js'):
                return self.send(200, (ROOT / self.path[1:]).read_bytes(), 'application/javascript; charset=utf-8')
            if self.path == '/api/templates':
                return self.send(200, TEMPLATES)
            if self.path == '/api/demo':
                return self.send(200, {'enabled': demo_mode})
            if self.path == '/api/evaluations':
                return self.send(200, evaluations.results(store))
            if self.path == '/api/submission':
                return self.send(200, submission.state(store))
            if self.path == '/api/readiness':
                return self.send(200, {**readiness.configuration(), 'last_check': readiness.latest()})
            if self.path == '/api/state':
                return self.send(200, {**store.state(), 'speech_ready': bool(os.getenv('GNANI_API_KEY')),
                    'reasoning_ready': all(os.getenv(k) for k in ('VOICEBRIDGE_LLM_URL', 'VOICEBRIDGE_LLM_KEY', 'VOICEBRIDGE_LLM_MODEL'))})
            return self.send(404, {'error': 'Not found.'})

        def do_POST(self):
            self.path = urlsplit(self.path).path
            origins = (f'http://127.0.0.1:{port}', f'http://localhost:{port}')
            if not self.allowed() or self.headers.get('Origin') not in origins:
                return self.send(403, {'error': 'Open the app locally to make changes.'})
            try:
                size = int(self.headers.get('Content-Length', 0))
                if not 0 < size <= 3_000_000:
                    raise ValueError('Request is empty or too large.')
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError('Expected an object.')
                if self.path == '/api/submission-save':
                    submission.save(store,data['item'],data['done'],data.get('evidence',''))
                    result = {'ok':True}
                elif self.path == '/api/evaluation-save':
                    evaluations.record(store,data['case_id'],data['status'],data['method'],data.get('notes',''))
                    result = {'ok':True}
                elif self.path == '/api/demo-reset':
                    result = {'sample_count': demo.reset(store, demo_mode, data.get('confirmed'))}
                elif self.path == '/api/backup-export':
                    result = backups.export(store)
                elif self.path == '/api/backup-preview':
                    result = backups.validate(data['backup'])
                elif self.path == '/api/backup-restore':
                    if data.get('confirmed') is not True:
                        raise ValueError('Review and confirm the backup first.')
                    result = backups.restore(store, data['backup'])
                elif self.path == '/api/sources':
                    result = {'id': store.source(data['title'], data['transcript'], data['language'])}
                elif self.path == '/api/tasks':
                    result = {'id': store.task(data['source_id'], data['title'], data['quote'], data.get('owner'), data.get('due'), data['revision'])}
                elif self.path == '/api/correct':
                    store.correct(data['source_id'], data['title'], data['transcript'], data['language'], data['revision'])
                    result = {'ok': True}
                elif self.path == '/api/delete':
                    store.delete(data['source_id'], data['revision'])
                    result = {'ok': True}
                elif self.path == '/api/review-task':
                    store.review_task(data['id'], data['title'], data['quote'], data.get('owner'), data.get('due'), data['revision'])
                    result = {'ok': True}
                elif self.path == '/api/task-edit':
                    store.review_task(data['id'], data['title'], data['quote'], data.get('owner'), data.get('due'), data['revision'], data['version'])
                    result = {'ok': True}
                elif self.path == '/api/task-remove':
                    store.remove_task(data['id'], data['version'])
                    result = {'ok': True}
                elif self.path == '/api/status':
                    store.status(data['id'], data['status'])
                    result = {'ok': True}
                elif self.path == '/api/search':
                    result = {'sources': store.search(data['question'])}
                elif self.path == '/api/summary-generate':
                    source = next(s for s in store.state()['sources'] if s['id'] == data['source_id'])
                    passages = summaries.generate(source, data['mode'], data['language'])
                    latest = next(s for s in store.state()['sources'] if s['id'] == source['id'])
                    if latest['revision'] != source['revision']:
                        raise ValueError('Source changed while generating. Try again.')
                    result = {'source_id': source['id'], 'revision': source['revision'],
                              'mode': data['mode'], 'language': data['language'], 'passages': passages}
                elif self.path == '/api/summary-save':
                    summaries.save(store, data['source_id'], data['revision'], data['mode'], data['language'], data['passages'])
                    result = {'ok': True}
                elif self.path == '/api/summary-list':
                    result = {'notes': summaries.saved(store, data['source_id'])}
                elif self.path == '/api/ask':
                    snapshot = store.state()
                    before = fingerprint(snapshot, data['source_ids'])
                    result = answer(snapshot, data['source_ids'], data['mode'], data.get('question', ''))
                    if fingerprint(store.state(), data['source_ids']) != before:
                        raise ValueError('Selected sources or tasks changed. Ask again for a current answer.')
                elif self.path == '/api/report':
                    result = {'report': build_report(store.state(), data['source_id'], data.get('template', 'team_handover'), data.get('fields', {}), data['revision'])}
                elif self.path == '/api/propose':
                    source = next(s for s in store.state()['sources'] if s['id'] == data['source_id'])
                    result = providers.propose(source['transcript'])
                    latest = next(s for s in store.state()['sources'] if s['id'] == source['id'])
                    if latest['revision'] != source['revision']:
                        raise ValueError('Source changed while generating. Generate a fresh proposal.')
                    result.update(source_id=source['id'], revision=source['revision'])
                elif self.path == '/api/transcribe':
                    result = {'transcript': providers.transcribe(base64.b64decode(data['audio'], validate=True), data['language'])}
                elif self.path == '/api/speak':
                    audio = providers.synthesize(data['text'], data.get('language', 'auto'))
                    return self.send(200, audio, 'audio/wav')
                else:
                    return self.send(404, {'error': 'Not found.'})
                self.send(200, result)
            except (ValueError, KeyError, TypeError, StopIteration) as error:
                self.send(400, {'error': str(error) if isinstance(error, ValueError) else 'Invalid request or missing record.'})
            except HTTPError as error:
                self.send(502, {'error': f'Provider HTTP {error.code}. No retry made; check access and credits.'})
            except (URLError, TimeoutError, OSError):
                self.send(502, {'error': 'Network or storage operation failed. No retry made.'})
            except Exception:
                self.send(500, {'error': 'Operation failed. Provider response and secrets hidden.'})
    return Handler


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8770)
    parser.add_argument('--speech-key', action='store_true')
    parser.add_argument('--reasoning-setup', action='store_true')
    parser.add_argument('--demo', action='store_true', help='Use isolated synthetic rehearsal workspace.')
    args = parser.parse_args()
    if args.speech_key:
        os.environ['GNANI_API_KEY'] = getpass.getpass('Gnani key (hidden, memory only): ')
    if args.reasoning_setup:
        os.environ['VOICEBRIDGE_LLM_URL'] = input('Reasoning HTTPS chat-completions URL: ').strip()
        os.environ['VOICEBRIDGE_LLM_MODEL'] = input('Reasoning model ID: ').strip()
        os.environ['VOICEBRIDGE_LLM_KEY'] = getpass.getpass('Reasoning API key (hidden, memory only): ')
    (ROOT / 'local_data').mkdir(exist_ok=True)
    store = Workspace(ROOT / 'local_data' / ('demo.sqlite3' if args.demo else 'workspace.sqlite3'))
    if args.demo:
        demo.seed(store)
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(store, args.port, args.demo))
    except OSError:
        raise SystemExit(f'Port {args.port} is occupied. Try --port {args.port + 1}.')
    print(f'VoiceBridge ready: http://127.0.0.1:{args.port}/ — keep this window open.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
