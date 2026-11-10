"""Local, evidence-linked workspace. No external calls in this module."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone


class Workspace:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, transcript TEXT NOT NULL,
                language TEXT NOT NULL, created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id),
                title TEXT NOT NULL, owner TEXT, due TEXT, quote TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('open','done')));
            ''')
            # Additive migration preserves existing local records.
            for table, column, definition in (
                ('sources', 'revision', 'INTEGER NOT NULL DEFAULT 1'),
                ('tasks', 'source_revision', 'INTEGER NOT NULL DEFAULT 1'),
                ('tasks', 'needs_review', 'INTEGER NOT NULL DEFAULT 0'),
                ('tasks', 'version', 'INTEGER NOT NULL DEFAULT 1')):
                if column not in {r['name'] for r in db.execute(f'PRAGMA table_info({table})')}:
                    db.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
            db.execute('''CREATE TABLE IF NOT EXISTS reviewed_notes (
                source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
                revision INTEGER NOT NULL, mode TEXT NOT NULL, language TEXT NOT NULL,
                passages TEXT NOT NULL, PRIMARY KEY(source_id,mode,language))''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def state(self):
        with self.connect() as db:
            db.execute('BEGIN')
            return {table: [dict(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY rowid DESC')]
                    for table in ('sources', 'tasks')}

    def source(self, title, transcript, language):
        title, transcript = title.strip(), transcript.strip()
        if not title or not transcript or len(title) > 160 or len(transcript) > 12000:
            raise ValueError('Enter a title (up to 160 characters) and a transcript (up to 12,000).')
        if language not in ('te-IN', 'en-IN', 'hi-IN'):
            raise ValueError('Unsupported language.')
        source_id = uuid.uuid4().hex
        with self.connect() as db:
            db.execute('INSERT INTO sources (id,title,transcript,language,created) VALUES (?,?,?,?,?)',
                       (source_id, title, transcript, language, datetime.now(timezone.utc).isoformat()))
        return source_id

    def task(self, source_id, title, quote, owner=None, due=None, revision=None):
        title, quote = title.strip(), quote.strip()
        with self.connect() as db:
            source = db.execute('SELECT * FROM sources WHERE id=?', (source_id,)).fetchone()
            if revision is not None and (not source or source['revision'] != revision):
                raise ValueError('Source changed. Reload and review the latest transcript.')
            if not source or not quote or quote not in source['transcript']:
                raise ValueError('Evidence must be an exact excerpt from the selected source.')
            if not title or len(title) > 300:
                raise ValueError('Task title must contain 1–300 characters.')
            if owner is not None and (not isinstance(owner, str) or len(owner) > 160):
                raise ValueError('Owner must be at most 160 characters.')
            if due:
                from datetime import date
                date.fromisoformat(due)
            task_id = uuid.uuid4().hex
            db.execute('INSERT INTO tasks (id,source_id,title,owner,due,quote,status,source_revision) VALUES (?,?,?,?,?,?,?,?)',
                       (task_id, source_id, title, (owner or '').strip() or None,
                        due or None, quote, 'open', source['revision']))
        return task_id

    def status(self, task_id, status):
        if status not in ('open', 'done'):
            raise ValueError('Invalid task status.')
        with self.connect() as db:
            if db.execute('UPDATE tasks SET status=?,version=version+1 WHERE id=? AND needs_review=0', (status, task_id)).rowcount != 1:
                raise ValueError('Task not found or source changed. Review the task first.')

    def correct(self, source_id, title, transcript, language, revision):
        title, transcript = title.strip(), transcript.strip()
        if not title or not transcript or len(title) > 160 or len(transcript) > 12000:
            raise ValueError('Enter a valid title and transcript.')
        if language not in ('te-IN', 'en-IN', 'hi-IN'):
            raise ValueError('Unsupported language.')
        with self.connect() as db:
            if db.execute('UPDATE sources SET title=?,transcript=?,language=?,revision=revision+1 WHERE id=? AND revision=?',
                          (title, transcript, language, source_id, revision)).rowcount != 1:
                raise ValueError('Source changed or was deleted. Reload before editing.')
            db.execute('UPDATE tasks SET needs_review=1,version=version+1 WHERE source_id=?', (source_id,))
            db.execute('DELETE FROM reviewed_notes WHERE source_id=?', (source_id,))

    def delete(self, source_id, revision):
        with self.connect() as db:
            source = db.execute('SELECT revision FROM sources WHERE id=?', (source_id,)).fetchone()
            if not source or source['revision'] != revision:
                raise ValueError('Source changed or was deleted. Reload before deleting.')
            db.execute('DELETE FROM tasks WHERE source_id=?', (source_id,))
            db.execute('DELETE FROM sources WHERE id=?', (source_id,))

    def review_task(self, task_id, title, quote, owner, due, revision, version=None):
        # Validate and replace atomically rather than silently approving old evidence.
        with self.connect() as db:
            task = db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
            if not task:
                raise ValueError('Task not found.')
            if version is not None and task['version'] != version:
                raise ValueError('Task changed. Refresh before editing again.')
            source = db.execute('SELECT * FROM sources WHERE id=?', (task['source_id'],)).fetchone()
            if source['revision'] != revision:
                raise ValueError('Source changed. Reload and review again.')
            if not title.strip() or len(title) > 300 or not quote.strip() or quote.strip() not in source['transcript']:
                raise ValueError('Enter a task title and exact evidence from the latest transcript.')
            if owner is not None and (not isinstance(owner, str) or len(owner) > 160):
                raise ValueError('Owner must be at most 160 characters.')
            if due:
                from datetime import date
                date.fromisoformat(due)
            db.execute('UPDATE tasks SET title=?,quote=?,owner=?,due=?,source_revision=?,needs_review=0,version=version+1 WHERE id=?',
                       (title.strip(), quote.strip(), (owner or '').strip() or None, due or None, revision, task_id))

    def remove_task(self, task_id, version):
        with self.connect() as db:
            if db.execute('DELETE FROM tasks WHERE id=? AND version=?', (task_id, version)).rowcount != 1:
                raise ValueError('Task changed or was removed. Refresh before removing it.')

    def search(self, question):
        # Deliberately labelled literal search, not semantic AI question answering.
        query = question.strip().casefold()
        if not query:
            return []
        return [s for s in self.state()['sources']
                if query in (s['title'] + ' ' + s['transcript']).casefold()][:10]

    def report(self, source_id):
        state = self.state()
        source = next((s for s in state['sources'] if s['id'] == source_id), None)
        if not source:
            raise ValueError('Source not found.')
        tasks = [t for t in state['tasks'] if t['source_id'] == source_id]
        lines = [f"# {source['title']}", '', '## Original transcript', source['transcript'], '',
                 '## Reviewed tasks']
        for t in tasks:
            if t['needs_review']:
                lines += [f"- NEEDS REVIEW: {t['title']} (source changed; prior evidence not approved)"]
                continue
            lines += [f"- [{'x' if t['status'] == 'done' else ' '}] {t['title']}",
                      f"  Owner: {t['owner'] or 'Unassigned'} | Due: {t['due'] or 'Unspecified'}",
                      f"  Evidence: {t['quote']}"]
        if not tasks:
            lines.append('No reviewed tasks yet.')
        lines += ['', f"Source: {source['id']}", 'Generated from saved records; no AI summary added.']
        return '\n'.join(lines)


def validate_proposal(raw, transcript):
    if not isinstance(raw, dict) or not isinstance(raw.get('summary'), str):
        raise ValueError('Model did not return a valid summary.')
    tasks = raw.get('tasks')
    if not isinstance(tasks, list) or len(tasks) > 20 or len(raw['summary']) > 4000:
        raise ValueError('Model returned an invalid proposal.')
    clean = []
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError('Invalid proposed task.')
        title, quote = task.get('title'), task.get('quote')
        if not isinstance(title, str) or not 0 < len(title) <= 300:
            raise ValueError('Invalid proposed task title.')
        if not isinstance(quote, str) or not quote or quote not in transcript:
            raise ValueError('Model evidence does not match the source. Proposal rejected.')
        # Owners/dates intentionally left for explicit human review in first release.
        clean.append({'title': title, 'quote': quote})
    return {'summary': raw['summary'], 'tasks': clean}
