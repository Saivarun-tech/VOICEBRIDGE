"""Human-observed evaluation records; never infer a pass from implementation."""
from datetime import datetime, timezone
CASES = {
 'telugu_quantity': 'Recognize Telugu quantities: rendu blue pens, moodu notebooks',
 'english_capture': 'Capture a short English handover using the microphone',
 'mixed_names': 'Preserve names in Telugu-English speech',
 'negation': 'Preserve not approved / ఇంకా approval లేదు',
 'noise': 'Try a consented synthetic recording with background noise',
 'record_limit': 'Verify recording stops within 29 seconds',
 'transcript_edit': 'Correct a transcript before saving',
 'task_extract': 'Extract explicit actions without inventing commitments',
 'task_unknowns': 'Leave missing owner and deadline unspecified',
 'task_review': 'Verify task evidence and explicit review before acceptance',
 'task_edit': 'Edit owner/date and verify saved task after restart',
 'correction': 'Correct a source and verify task re-review is required',
 'summary_te': 'Review Telugu summary meaning against the original',
 'translation_hi': 'Review Hindi translation meaning and completeness',
 'reports': 'Export all three report templates; verify unknown details',
 'qa_supported': 'Ask a supported question and verify each source quote',
 'qa_unknown': 'Ask an unsupported question and verify abstention',
 'tts': 'Listen to Gnani readback and check names, quantities and negation',
 'backup': 'Export and restore a trusted backup into the demo workspace',
 'deletion': 'Delete a synthetic source and verify dependent data clears',
}


def initialize(store):
    with store.connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS evaluations (
            case_id TEXT PRIMARY KEY, status TEXT NOT NULL, method TEXT NOT NULL,
            notes TEXT NOT NULL, checked_at TEXT NOT NULL)''')


def record(store, case_id, status, method, notes):
    if case_id not in CASES or status not in ('passed', 'failed', 'blocked', 'not_tested'):
        raise ValueError('Choose a known test case and valid status.')
    if method not in ('live_provider', 'manual_local', 'mocked', 'not_tested'):
        raise ValueError('Choose how the test was performed.')
    if not isinstance(notes, str) or len(notes) > 2000:
        raise ValueError('Observation must be at most 2,000 characters.')
    if status != 'not_tested' and (method == 'not_tested' or not notes.strip()):
        raise ValueError('Record the test method and an actual observation.')
    initialize(store)
    with store.connect() as db:
        db.execute('INSERT OR REPLACE INTO evaluations VALUES (?,?,?,?,?)',
                   (case_id,status,method,notes.strip(),datetime.now(timezone.utc).isoformat()))


def results(store):
    initialize(store)
    with store.connect() as db:
        saved = {r['case_id']: dict(r) for r in db.execute('SELECT * FROM evaluations')}
    cases = [{'case_id':key,'title':title, **saved.get(key,{'status':'not_tested','method':'not_tested','notes':'','checked_at':None})}
             for key,title in CASES.items()]
    counts = {status:sum(c['status']==status for c in cases) for status in ('passed','failed','blocked','not_tested')}
    return {'cases':cases,'counts':counts,'limitation':'User-recorded observations, not automatic certification. Mocked/local passes do not establish live AI quality. Latest result per case only; API costs and eligibility are not verified.'}
