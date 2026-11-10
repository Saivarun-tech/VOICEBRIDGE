import copy
import tempfile
import unittest
from pathlib import Path
from core import Workspace
import backups
import summaries


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Workspace(Path(self.tmp.name)/'test.db')
        self.sid = self.ws.source('తెలుగు', 'రెండు పెన్నులు కావాలి.', 'te-IN')
        self.ws.task(self.sid, 'Review pens', 'రెండు పెన్నులు కావాలి.')
        summaries.save(self.ws, self.sid, 1, 'summary', 'en-IN', [{'text':'Two pens needed.', 'quote':'రెండు పెన్నులు కావాలి.'}])

    def tearDown(self):
        self.tmp.cleanup()

    def test_roundtrip_new_ids_and_existing_work(self):
        data = backups.export(self.ws)
        self.assertEqual(backups.restore(self.ws, data), {'sources':1,'tasks':1,'reviewed_notes':1})
        state = self.ws.state()
        self.assertEqual(len(state['sources']), 2)
        restored = next(s for s in state['sources'] if s['id'] != self.sid)
        self.assertEqual(summaries.saved(self.ws, restored['id'])[0]['passages'], data['reviewed_notes'][0]['passages'])
        with self.assertRaises(ValueError):
            backups.restore(self.ws, data)
        self.assertEqual(len(self.ws.state()['sources']), 2)

    def test_invalid_backup_changes_nothing(self):
        data = backups.export(self.ws)
        for mutation in ('quote','reference','version','duplicate'):
            bad = copy.deepcopy(data)
            if mutation=='quote': bad['tasks'][0]['quote']='invented'
            if mutation=='reference': bad['tasks'][0]['source_id']='missing'
            if mutation=='version': bad['version']=2
            if mutation=='duplicate': bad['sources'].append(bad['sources'][0])
            with self.assertRaises(ValueError): backups.restore(self.ws,bad)
            self.assertEqual(len(self.ws.state()['sources']),1)

    def test_stale_tasks_keep_review_flag(self):
        self.ws.correct(self.sid, 'Corrected', 'No pens.', 'en-IN', 1)
        data = backups.export(self.ws)
        backups.restore(self.ws,data)
        self.assertTrue(all(t['needs_review'] for t in self.ws.state()['tasks']))

    def test_export_has_no_keys_or_configuration(self):
        data = backups.export(self.ws)
        self.assertEqual(set(data), {'format','version','exported_at','sources','tasks','reviewed_notes'})
