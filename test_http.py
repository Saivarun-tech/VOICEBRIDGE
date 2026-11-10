import json
import tempfile
import threading
import unittest
from pathlib import Path
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from app import handler_for
from core import Workspace


class LocalHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Workspace(Path(self.tmp.name)/'test.db')
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(self.store,0))
        self.port=self.server.server_address[1]
        self.server.RequestHandlerClass=handler_for(self.store,self.port)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()

    def request(self,method,path,body=None,origin=True):
        connection=HTTPConnection('127.0.0.1',self.port,timeout=5)
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=f'http://127.0.0.1:{self.port}'
        connection.request(method,path,json.dumps(body) if body is not None else None,headers)
        result=connection.getresponse();status=result.status;data=result.read();connection.close();return status,data

    def test_view_query_reload_serves_page(self):
        status,data=self.request('GET','/?view=reports')
        self.assertEqual(status,200);self.assertIn(b'VoiceBridge',data)

    def test_no_origin_mutation_blocked(self):
        status,_=self.request('POST','/api/sources',{'title':'Injected','transcript':'x','language':'en-IN'},origin=False)
        self.assertEqual(status,403);self.assertEqual(self.store.state()['sources'],[])

    def test_failed_evidence_preserves_saved_data(self):
        sid=self.store.source('Note','No approval.','en-IN')
        status,_=self.request('POST','/api/tasks',{'source_id':sid,'revision':1,'title':'Buy','quote':'Approved'})
        self.assertEqual(status,400);self.assertEqual(len(self.store.state()['sources']),1);self.assertEqual(self.store.state()['tasks'],[])
