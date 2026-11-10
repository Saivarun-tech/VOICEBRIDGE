"""Synthetic browser regression in disposable databases, never the user's workspace."""
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from http.server import ThreadingHTTPServer
from core import Workspace
from app import handler_for
import demo

ROOT=Path(__file__).resolve().parent
CHECKS=['browser-check.cjs','voice-check.cjs','readiness-check.cjs','reports-check.cjs','lifecycle-check.cjs','ask-check.cjs','summaries-check.cjs',
        'tasks-check.cjs','backups-check.cjs','demo-check.cjs','evaluations-check.cjs',
        'submission-check.cjs','ui-check.cjs','recording-check.cjs','release-check.cjs','polish-check.cjs','global-recording-check.cjs']


def main():
    for key in ('GNANI_API_KEY','VOICEBRIDGE_LLM_URL','VOICEBRIDGE_LLM_MODEL','VOICEBRIDGE_LLM_KEY'):
        os.environ.pop(key,None)
    servers=[]
    with tempfile.TemporaryDirectory(prefix='voicebridge-qa-') as temp:
        try:
            ports=[]
            for mode in (False,True):
                store=Workspace(Path(temp)/('demo.db' if mode else 'normal.db'))
                if mode:demo.seed(store)
                server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(store,0,mode))
                port=server.server_address[1];ports.append(port)
                server.RequestHandlerClass=handler_for(store,port,mode)
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();servers.append((server,thread))
            for index,name in enumerate(CHECKS):
                source=(ROOT/name).read_text(encoding='utf-8')
                suffix='' if name in ('ui-check.cjs','recording-check.cjs','polish-check.cjs','global-recording-check.cjs') else '?view=all'
                for old,new in zip((8772,8774),ports):
                    source=source.replace(f'http://127.0.0.1:{old}/',f'http://127.0.0.1:{new}/{suffix}')
                for old in (8770,8771):
                    source=source.replace(f'http://127.0.0.1:{old}/',f'http://127.0.0.1:{ports[0]}/{suffix}')
                # Failing browser checks must terminate instead of leaving Edge alive.
                source=source.replace('process.exitCode=1','process.exit(1)')
                script=Path(temp)/name;script.write_text(source,encoding='utf-8')
                print(f'{index+1}/{len(CHECKS)} {name}',flush=True)
                result=subprocess.run(['D:/node.exe',str(script)],cwd=ROOT,timeout=50,capture_output=True,text=True)
                print(result.stdout.strip(),flush=True)
                if result.returncode:
                    print(result.stderr,flush=True)
                    return result.returncode
            print('All isolated browser checks passed. No user databases used.',flush=True)
            return 0
        finally:
            for server,thread in servers:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':
    raise SystemExit(main())
