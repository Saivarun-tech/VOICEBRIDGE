"""Synthetic, explicitly labelled rehearsal data. No model outputs are fabricated."""
SAMPLES = [
    ('demo-handover', 'SYNTHETIC · Team handover',
     'రవి projector check చేస్తాడు. Anita slides పంపుతుంది. Room booking ఇంకా confirm కాలేదు. Budget approval లేదు.'),
    ('demo-request', 'SYNTHETIC · Customer request',
     'నాకు రెండు blue pens, మూడు notebooks కావాలి. Delivery date ఇంకా decide చేయలేదు. Meena stock check చేసి చెప్తుంది.'),
    ('demo-service', 'SYNTHETIC · Service update',
     'Printer paper jam అవుతోంది. Cleaning పూర్తి అయింది. Replacement part కి approval ఇంకా రాలేదు. Kiran customer కి update ఇస్తాడు.'),
]


def seed(store):
    from datetime import datetime, timezone
    with store.connect() as db:
        added = 0
        for sid, title, transcript in SAMPLES:
            added += db.execute('INSERT OR IGNORE INTO sources (id,title,transcript,language,created,revision) VALUES (?,?,?,?,?,1)',
                                (sid, title, transcript, 'te-IN', datetime.now(timezone.utc).isoformat())).rowcount
    return added


def reset(store, enabled, confirmed):
    if not enabled or confirmed is not True:
        raise ValueError('Reset is available only in explicitly confirmed demo mode.')
    with store.connect() as db:
        db.execute('DELETE FROM tasks')
        db.execute('DELETE FROM sources')
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='restored_backups'").fetchone():
            db.execute('DELETE FROM restored_backups')
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='evaluations'").fetchone():
            db.execute('DELETE FROM evaluations')
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='submission_items'").fetchone():
            db.execute('DELETE FROM submission_items')
    return seed(store)
