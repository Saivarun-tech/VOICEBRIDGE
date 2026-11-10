"""Versioned JSON export and validated, atomic copy restore."""
from datetime import date, datetime, timezone
import hashlib
import json
import uuid
import summaries

LIMIT = 2_500_000


def export(store):
    with store.connect() as db:
        db.execute('BEGIN')
        data = {table: [dict(row) for row in db.execute(f'SELECT * FROM {table}')]
                for table in ('sources', 'tasks', 'reviewed_notes')}
    for note in data['reviewed_notes']:
        note['passages'] = json.loads(note['passages'])
    result = {'format': 'voicebridge-backup', 'version': 1,
              'exported_at': datetime.now(timezone.utc).isoformat(), **data}
    if len(json.dumps(result, ensure_ascii=False).encode()) > LIMIT:
        raise ValueError('Workspace exceeds the JSON backup limit. Keep a local database copy while the app is stopped.')
    return result


def text(value, maximum, blank=False):
    if not isinstance(value, str) or len(value) > maximum or (not blank and not value.strip()):
        raise ValueError('Backup contains invalid text fields.')
    return value


def integer(value):
    if type(value) is not int or not 1 <= value <= 1_000_000_000:
        raise ValueError('Backup contains an invalid revision.')
    return value


def validate(data):
    if not isinstance(data, dict) or data.get('format') != 'voicebridge-backup' or type(data.get('version')) is not int or data['version'] != 1:
        raise ValueError('Unsupported backup format or version.')
    if len(json.dumps(data, ensure_ascii=False).encode()) > LIMIT:
        raise ValueError('Backup exceeds 2.5 MB.')
    for key, maximum in (('sources', 200), ('tasks', 2000), ('reviewed_notes', 1200)):
        if not isinstance(data.get(key), list) or len(data[key]) > maximum or any(not isinstance(row, dict) for row in data[key]):
            raise ValueError('Backup has invalid records or exceeds the record limit.')
    ids = {}
    for source in data['sources']:
        sid = text(source.get('id'), 100)
        if sid in ids:
            raise ValueError('Duplicate source ID in backup.')
        ids[sid] = source
        text(source.get('title'), 160)
        text(source.get('transcript'), 12000)
        if source.get('language') not in summaries.LANGUAGES:
            raise ValueError('Invalid source language.')
        integer(source.get('revision'))
        datetime.fromisoformat(text(source.get('created'), 100))
    seen = set()
    for task in data['tasks']:
        tid = text(task.get('id'), 100)
        if tid in seen:
            raise ValueError('Duplicate task ID in backup.')
        seen.add(tid)
        source = ids.get(task.get('source_id'))
        if not source or task.get('status') not in ('open', 'done') or type(task.get('needs_review')) is not int or task['needs_review'] not in (0, 1):
            raise ValueError('Invalid task reference or status.')
        text(task.get('title'), 300)
        quote = text(task.get('quote'), 12000)
        revision = integer(task.get('source_revision'))
        integer(task.get('version'))
        if not task['needs_review'] and (quote not in source['transcript'] or revision != source['revision']):
            raise ValueError('Reviewed task evidence does not match its source.')
        if task.get('owner') is not None:
            text(task['owner'], 160, blank=True)
        if task.get('due'):
            date.fromisoformat(text(task['due'], 10))
        elif task.get('due') not in (None, ''):
            raise ValueError('Invalid due date.')
    seen = set()
    for note in data['reviewed_notes']:
        source = ids.get(note.get('source_id'))
        if not source or note.get('mode') not in ('summary', 'translation') or note.get('language') not in summaries.LANGUAGES:
            raise ValueError('Invalid reviewed note reference.')
        if integer(note.get('revision')) != source['revision']:
            raise ValueError('Reviewed note is from an outdated source revision.')
        summaries.validate(note.get('passages'), source['transcript'])
        key = (note['source_id'], note['mode'], note['language'])
        if key in seen:
            raise ValueError('Duplicate reviewed note.')
        seen.add(key)
    return {'sources': len(data['sources']), 'tasks': len(data['tasks']), 'reviewed_notes': len(data['reviewed_notes'])}


def restore(store, data):
    counts = validate(data)
    mapping = {source['id']: uuid.uuid4().hex for source in data['sources']}
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    with store.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS restored_backups (digest TEXT PRIMARY KEY)')
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM restored_backups WHERE digest=?', (digest,)).fetchone():
            raise ValueError('This exact backup has already been restored. No records added.')
        for source in data['sources']:
            db.execute('INSERT INTO sources (id,title,transcript,language,created,revision) VALUES (?,?,?,?,?,?)',
                       (mapping[source['id']], source['title'], source['transcript'], source['language'], source['created'], source['revision']))
        for task in data['tasks']:
            db.execute('INSERT INTO tasks (id,source_id,title,owner,due,quote,status,source_revision,needs_review,version) VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (uuid.uuid4().hex, mapping[task['source_id']], task['title'], task.get('owner'), task.get('due'),
                        task['quote'], task['status'], task['source_revision'], task['needs_review'], 1))
        for note in data['reviewed_notes']:
            db.execute('INSERT INTO reviewed_notes VALUES (?,?,?,?,?)',
                       (mapping[note['source_id']], note['revision'], note['mode'], note['language'], json.dumps(note['passages'], ensure_ascii=False)))
        db.execute('INSERT INTO restored_backups VALUES (?)', (digest,))
    return counts
