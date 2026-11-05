"""Small helpers to build n8n workflow JSON for CLI import."""
import json
import uuid

SHEET_ID = '1uFc0RmztEiY9tcsNGLe0bExBuhJ5Zxjp6j-J7WfYYjc'
SHEETS_CRED = {'googleSheetsOAuth2Api': {'id': 'uVqG7fQd8cxSfaMU', 'name': 'order to delivery system'}}
GMAIL_CRED = {'gmailOAuth2': {'id': 'oOJ0vvQfmwr3MpT0', 'name': 'Demo Traders Gmail'}}
FORMS_CRED = {'httpBasicAuth': {'id': 'FKw937EGT3VSfiqE', 'name': 'Demo Traders Forms'}}
DOC = {'__rl': True, 'mode': 'id', 'value': SHEET_ID}
RETRY = {'retryOnFail': True, 'maxTries': 5, 'waitBetweenTries': 5000}


def nid():
    return str(uuid.uuid4())


def schema(cols):
    return [{'id': c, 'displayName': c, 'required': False, 'defaultMatch': False, 'display': True,
             'type': 'string', 'canBeUsedToMatch': True} for c in cols]


class Wf:
    def __init__(self, wid, name):
        self.wid = wid
        self.name = name
        self.nodes = []
        self.links = []
        self.x = 0

    def add(self, node, pos=None):
        node['id'] = nid()
        if pos is None:
            pos = [self.x, 0]
            self.x += 240
        node['position'] = pos
        self.nodes.append(node)
        return node['name']

    def link(self, a, b, out=0):
        self.links.append((a, b, out))

    def chain(self, *names):
        for a, b in zip(names, names[1:]):
            self.link(a, b)

    def build(self):
        conns = {}
        for a, b, out in self.links:
            c = conns.setdefault(a, {'main': []})
            while len(c['main']) <= out:
                c['main'].append([])
            c['main'][out].append({'node': b, 'type': 'main', 'index': 0})
        names = [n['name'] for n in self.nodes]
        assert len(names) == len(set(names)), 'duplicate node names'
        for a, b, _ in self.links:
            assert a in names and b in names, 'bad link %s -> %s' % (a, b)
        return [{'id': self.wid, 'name': self.name, 'active': False, 'nodes': self.nodes, 'connections': conns,
                 'settings': {'executionOrder': 'v1', 'timezone': 'America/Santo_Domingo', 'availableInMCP': True},
                 'pinData': {}, 'tags': []}]

    def save(self, path):
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(self.build(), f, ensure_ascii=False, indent=2)
        print('saved', path, 'nodes:', len(self.nodes))


def manual(name='Start'):
    return {'name': name, 'type': 'n8n-nodes-base.manualTrigger', 'typeVersion': 1, 'parameters': {}}


def code(name, js, notes=None):
    n = {'name': name, 'type': 'n8n-nodes-base.code', 'typeVersion': 2,
         'parameters': {'mode': 'runOnceForAllItems', 'language': 'javaScript', 'jsCode': js}}
    if notes:
        n['notes'] = notes
    return n


def if_bool(name, left):
    return {'name': name, 'type': 'n8n-nodes-base.if', 'typeVersion': 2.4,
            'parameters': {'conditions': {'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'strict'},
                                          'conditions': [{'id': nid(), 'leftValue': left, 'rightValue': '',
                                                          'operator': {'type': 'boolean', 'operation': 'true', 'singleValue': True}}],
                                          'combinator': 'and'}, 'options': {}}}


def sheet_read(name, tab, always=False, once=False):
    n = {'name': name, 'type': 'n8n-nodes-base.googleSheets', 'typeVersion': 4.7, 'credentials': SHEETS_CRED,
         'parameters': {'resource': 'sheet', 'operation': 'read', 'documentId': DOC,
                        'sheetName': {'__rl': True, 'mode': 'name', 'value': tab}}}
    n.update(RETRY)
    if always:
        n['alwaysOutputData'] = True
    if once:
        n['executeOnce'] = True
    return n


def sheet_append(name, tab, cols, values):
    n = {'name': name, 'type': 'n8n-nodes-base.googleSheets', 'typeVersion': 4.7, 'credentials': SHEETS_CRED,
         'parameters': {'resource': 'sheet', 'operation': 'append', 'documentId': DOC,
                        'sheetName': {'__rl': True, 'mode': 'name', 'value': tab},
                        'columns': {'mappingMode': 'defineBelow', 'value': values, 'schema': schema(cols)},
                        'options': {'cellFormat': 'RAW'}}}
    n.update(RETRY)
    return n


def sheet_update(name, tab, match, cols, values):
    n = {'name': name, 'type': 'n8n-nodes-base.googleSheets', 'typeVersion': 4.7, 'credentials': SHEETS_CRED,
         'parameters': {'resource': 'sheet', 'operation': 'update', 'documentId': DOC,
                        'sheetName': {'__rl': True, 'mode': 'name', 'value': tab},
                        'columns': {'mappingMode': 'defineBelow', 'value': values, 'matchingColumns': [match],
                                    'schema': [dict(s, canBeUsedToMatch=(s['id'] == match)) for s in schema(cols)]},
                        'options': {'cellFormat': 'RAW'}}}
    n.update(RETRY)
    return n


LOG_COLS = ['Time', 'Agent', 'Action', 'Ref_ID', 'Details']


def log_node(name, agent, action, ref_expr, details_expr):
    return sheet_append(name, 'Activity_Log', LOG_COLS, {
        'Time': '={{ $now.toFormat("yyyy-MM-dd HH:mm:ss") }}', 'Agent': agent, 'Action': action,
        'Ref_ID': ref_expr, 'Details': details_expr})


def notify_call(name, wf_id, ref, event, subject_expr, message_expr):
    """ref is an expression prefix such as $("Plan").first().json"""
    def f(k):
        return '={{ %s.%s }}' % (ref, k)
    fields = ['order_id', 'event', 'customer_name', 'customer_email', 'customer_phone', 'subject', 'message']
    return {'name': name, 'type': 'n8n-nodes-base.executeWorkflow', 'typeVersion': 1.4, 'alwaysOutputData': True,
            'parameters': {'source': 'database',
                           'workflowId': {'__rl': True, 'mode': 'id', 'value': wf_id, 'cachedResultName': 'Demo Traders - Notify Customer'},
                           'workflowInputs': {'mappingMode': 'defineBelow',
                                              'value': {'order_id': f('order_id'), 'event': event,
                                                        'customer_name': f('customer_name'), 'customer_email': f('customer_email'),
                                                        'customer_phone': f('customer_phone'), 'subject': subject_expr,
                                                        'message': message_expr},
                                              'matchingColumns': [],
                                              'schema': [{'id': k, 'displayName': k, 'required': False, 'defaultMatch': False,
                                                          'display': True, 'canBeUsedToMatch': False, 'type': 'string'} for k in fields],
                                              'attemptToConvertTypes': False, 'convertFieldsToString': False},
                           'mode': 'once', 'options': {'waitForSubWorkflow': True}}}


def form_trigger(name, title, desc, fields, path):
    return {'name': name, 'type': 'n8n-nodes-base.formTrigger', 'typeVersion': 2.6, 'credentials': FORMS_CRED,
            'webhookId': nid(),
            'parameters': {'authentication': 'basicAuth', 'formTitle': title, 'formDescription': desc,
                           'formFields': {'values': fields}, 'responseMode': 'lastNode',
                           'options': {'appendAttribution': False, 'path': path}}}


def form_done(name, title, message_expr):
    return {'name': name, 'type': 'n8n-nodes-base.form', 'typeVersion': 2.5,
            'parameters': {'operation': 'completion', 'respondWith': 'text', 'completionTitle': title,
                           'completionMessage': message_expr, 'options': {'appendAttribution': False}}}


def http_sheets(name, method, url, body):
    return {'name': name, 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.5, 'credentials': SHEETS_CRED,
            'parameters': {'method': method, 'url': url, 'authentication': 'predefinedCredentialType',
                           'nodeCredentialType': 'googleSheetsOAuth2Api', 'sendBody': True, 'contentType': 'json',
                           'specifyBody': 'json', 'jsonBody': json.dumps(body, ensure_ascii=False), 'options': {}}}
