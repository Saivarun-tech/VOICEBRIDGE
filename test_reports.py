import tempfile
import unittest
from pathlib import Path
from core import Workspace
from reporting import TEMPLATES, build_report


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Workspace(Path(self.tmp.name) / 'test.db')
        self.sid = self.ws.source('Request', 'రెండు పెన్నులు కావాలి. Ravi will follow up. No approval yet.', 'te-IN')
        self.tid = self.ws.task(self.sid, 'Follow up', 'Ravi will follow up.', owner='Ravi')

    def tearDown(self):
        self.tmp.cleanup()

    def report(self, template='team_handover', fields=None, revision=1):
        return build_report(self.ws.state(), self.sid, template, fields or {}, revision)

    def test_all_three_distinct_templates_and_unknowns(self):
        for key, spec in TEMPLATES.items():
            result = self.report(key)
            self.assertIn(spec['name'], result)
            self.assertIn('Not specified / no excerpt selected.', result)
            self.assertIn('Due: Unspecified', result)

    def test_telugu_excerpt_and_separate_done_tasks(self):
        self.ws.status(self.tid, 'done')
        report = self.report('customer_request', {'request': 'రెండు పెన్నులు కావాలి.'})
        self.assertIn('## Completed follow-ups\n- [x] Follow up', report)
        self.assertIn('## Requested items / service\nరెండు పెన్నులు కావాలి.', report)

    def test_reject_invented_excerpt_unknown_template_and_field(self):
        for template, fields in [('service_update', {'approval': 'Approved'}), ('unknown', {}),
                                 ('team_handover', {'other': 'x'})]:
            with self.assertRaises(ValueError):
                self.report(template, fields)

    def test_stale_report_and_stale_task_handling(self):
        self.ws.correct(self.sid, 'Correction', 'Ravi will follow up. No approval yet.', 'en-IN', 1)
        with self.assertRaises(ValueError):
            self.report()
        result = self.report(revision=2)
        self.assertIn('NEEDS REVIEW: Follow up', result)
        self.assertNotIn('- [ ] Follow up', result)
