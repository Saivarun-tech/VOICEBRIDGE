"""Local submission preparation; never publishes or submits anything."""
from datetime import datetime, timezone
from urllib.parse import urlparse

ITEMS = {
    'eligibility': 'Student eligibility / personal-email exception verified',
    'speech': 'Gnani speech tested live and results reviewed',
    'reasoning': 'Reasoning, translation and grounded answers tested live',
    'user_tests': 'Manual test checklist completed; critical failures resolved',
    'ui': 'Final UI and accessibility reviewed',
    'demo': 'Working public demo video published with required tags',
    'code': 'Code and setup documentation prepared for review',
    'submitted': 'Official submission completed; confirmation saved',
}


def initialize(store):
    with store.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS submission_items (item TEXT PRIMARY KEY, done INTEGER NOT NULL, evidence TEXT NOT NULL, updated TEXT NOT NULL)')


def save(store, item, done, evidence):
    if item not in ITEMS or type(done) is not bool or not isinstance(evidence, str) or len(evidence) > 2000:
        raise ValueError('Invalid checklist item or evidence.')
    evidence = evidence.strip()
    if done and not evidence:
        raise ValueError('Add a link or a concrete verification note before marking complete.')
    if done and item == 'demo':
        parsed = urlparse(evidence)
        if parsed.scheme != 'https' or parsed.hostname not in ('linkedin.com','www.linkedin.com','x.com','www.x.com','twitter.com','www.twitter.com'):
            raise ValueError('Use the HTTPS LinkedIn or X URL of your actual public demo post.')
    initialize(store)
    with store.connect() as db:
        db.execute('INSERT OR REPLACE INTO submission_items VALUES (?,?,?,?)',
                   (item,int(done),evidence,datetime.now(timezone.utc).isoformat()))


def state(store):
    initialize(store)
    with store.connect() as db:
        saved = {row['item']:dict(row) for row in db.execute('SELECT * FROM submission_items')}
    items = [{'item':key,'title':title, **saved.get(key,{'done':0,'evidence':'','updated':None})} for key,title in ITEMS.items()]
    return {'items':items,'remaining':sum(not row['done'] for row in items),
            'notice':'User-maintained preparation checklist. This app does not verify public links, eligibility or submission, and does not publish or submit anything. Keep private details out of exported notes.'}
