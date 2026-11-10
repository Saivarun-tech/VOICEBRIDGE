"""Deterministic reports; field values are human-selected source excerpts."""
TEMPLATES = {
    'team_handover': {'name': 'Team handover', 'fields': {
        'context': 'Context / decisions', 'blockers': 'Blockers / unresolved questions'},
        'open': 'Pending work', 'done': 'Completed work'},
    'customer_request': {'name': 'Customer request', 'fields': {
        'request': 'Requested items / service', 'constraints': 'Customer constraints / preferences'},
        'open': 'Follow-up actions', 'done': 'Completed follow-ups'},
    'service_update': {'name': 'Service update', 'fields': {
        'issue': 'Reported issue', 'approval': 'Approval / authorization stated'},
        'open': 'Recommended / pending work', 'done': 'Completed actions'},
}


def build_report(state, source_id, template, fields, revision):
    source = next((s for s in state['sources'] if s['id'] == source_id), None)
    if not source:
        raise ValueError('Source not found.')
    if revision != source['revision']:
        raise ValueError('Source changed. Reload and review report excerpts again.')
    if template not in TEMPLATES:
        raise ValueError('Unknown report template.')
    spec = TEMPLATES[template]
    if not isinstance(fields, dict) or set(fields) - set(spec['fields']):
        raise ValueError('Invalid report fields.')
    for value in fields.values():
        if not isinstance(value, str) or len(value) > 4000:
            raise ValueError('Invalid report excerpt.')
        if value.strip() and value.strip() not in source['transcript']:
            raise ValueError('Report excerpts must exactly match the current transcript.')
    tasks = [t for t in state['tasks'] if t['source_id'] == source_id]
    lines = [f"# {spec['name']}: {source['title']}", '',
             f"Source: {source_id} | Revision: {source['revision']}",
             'Excerpt-based report. Section placement is user reviewed; no AI interpretation added.']
    for key, label in spec['fields'].items():
        lines += ['', f'## {label}', fields.get(key, '').strip() or 'Not specified / no excerpt selected.']
    for status in ('open', 'done'):
        lines += ['', f"## {spec[status]}"]
        reviewed = [t for t in tasks if t['status'] == status and not t['needs_review']]
        for task in reviewed:
            lines += [f"- [{'x' if status == 'done' else ' '}] {task['title']}",
                      f"  Owner: {task['owner'] or 'Unassigned'} | Due: {task['due'] or 'Unspecified'}",
                      f"  Evidence: {task['quote']}"]
        if not reviewed:
            lines.append('No reviewed tasks in this section.')
    stale = [t for t in tasks if t['needs_review']]
    if stale:
        lines += ['', '## Tasks requiring review']
        lines += [f"- NEEDS REVIEW: {t['title']} (source changed; prior evidence not approved)" for t in stale]
    lines += ['', '## Original transcript', source['transcript'], '',
              'Completion reflects user-marked task status. An excerpt does not establish authorization.',
              'Generated from saved records; no AI summary added.']
    return '\n'.join(lines)
