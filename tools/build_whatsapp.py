"""Builds the WhatsApp (OpenWA) gateway workflow and the WhatsApp branch of Notify Customer.

Usage:  WA_ALLOW=18095551234,18295559999 python tools/build_whatsapp.py OUT_DIR
Without WA_ALLOW the allowlist is empty: the bot answers nobody and sends nothing (safe default).
The allowlist is never committed; the repo copies are generated with an empty list.
"""
import json
import os
import sys
import uuid
import copy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'workflows')
ALLOW = [d for d in (''.join(c for c in x if c.isdigit()) for x in os.environ.get('WA_ALLOW', '').split(',')) if d]
SESSION = '9478bd38-41f3-4cb9-b9b2-b178948fbd56'
OWN_NUMBER = '18499192565'
OWA = 'http://localhost:2785/api/sessions/%s/messages/send-text' % SESSION
WH_PATH = os.environ.get('WA_PATH', 'wa-inbound-PLACEHOLDER')
CRED = {'httpHeaderAuth': {'id': 'OpenWAKey01', 'name': 'OpenWA API key'}}
SHEETS = {'googleSheetsOAuth2Api': {'id': 'uVqG7fQd8cxSfaMU', 'name': 'order to delivery system'}}
SHEET_ID = '1uFc0RmztEiY9tcsNGLe0bExBuhJ5Zxjp6j-J7WfYYjc'
LOG_COLS = ['Time', 'Agent', 'Action', 'Ref_ID', 'Details']


def nid():
    return str(uuid.uuid4())


def load(name):
    with open(os.path.join(ROOT, 'workflows', name), encoding='utf-8') as f:
        return json.load(f)


def log_node(name, agent, action, ref, details, pos):
    vals = {'Time': '={{ $now.toFormat("yyyy-MM-dd HH:mm:ss") }}', 'Agent': agent, 'Action': action,
            'Ref_ID': ref, 'Details': details}
    schema = [{'id': c, 'displayName': c, 'required': False, 'defaultMatch': False, 'display': True,
               'type': 'string', 'canBeUsedToMatch': True} for c in LOG_COLS]
    return {'id': nid(), 'name': name, 'type': 'n8n-nodes-base.googleSheets', 'typeVersion': 4.7, 'position': pos,
            'parameters': {'resource': 'sheet', 'operation': 'append',
                           'documentId': {'__rl': True, 'mode': 'id', 'value': SHEET_ID},
                           'sheetName': {'__rl': True, 'mode': 'name', 'value': 'Activity_Log'},
                           'columns': {'mappingMode': 'defineBelow', 'value': vals, 'schema': schema},
                           'options': {'cellFormat': 'RAW'}},
            'retryOnFail': True, 'maxTries': 5, 'waitBetweenTries': 5000, 'credentials': SHEETS}


def send_node(name, chat_expr, text_expr, pos):
    body = '={{ JSON.stringify({ chatId: %s, text: %s }) }}' % (chat_expr, text_expr)
    return {'id': nid(), 'name': name, 'type': 'n8n-nodes-base.httpRequest', 'typeVersion': 4.2, 'position': pos,
            'parameters': {'method': 'POST', 'url': OWA, 'authentication': 'genericCredentialType',
                           'genericAuthType': 'httpHeaderAuth', 'sendBody': True, 'specifyBody': 'json',
                           'jsonBody': body, 'options': {'timeout': 20000}},
            'credentials': CRED, 'onError': 'continueRegularOutput'}


def if_true(name, left, pos):
    cond = {'leftValue': left, 'operator': {'type': 'boolean', 'operation': 'true', 'singleValue': True}}
    return {'id': nid(), 'name': name, 'type': 'n8n-nodes-base.if', 'typeVersion': 2.4, 'position': pos,
            'parameters': {'conditions': {'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'strict'},
                                          'conditions': [cond], 'combinator': 'and'}}}


def link(*names):
    return [{'node': n, 'type': 'main', 'index': 0} for n in names]


# ---------------------------------------------------------------- gateway
fd = load('01-front-desk-agent.json')
by = {n['name']: n for n in fd['nodes']}
sysmsg = by['Front desk agent']['parameters']['options']['systemMessage'] + (
    "\n\nCHANNEL: WhatsApp. The first line of each message is '[WhatsApp customer, phone: <digits>]'. "
    "That is the customer's phone: use it, never ask for it again. Keep replies short (WhatsApp), no markdown tables, "
    "use plain text and line breaks. Never mention the bracket line to the customer.")

FILTER_JS = """// Why Code: validates the OpenWA webhook, applies the test allowlist and drops duplicates.
const ALLOW = __ALLOW__;   // numbers allowed to talk to the bot (digits with country code). Empty = nobody.
const OWN = '__OWN__';
const SELF_CHATS = ['55182427721886@lid'];   // the self chat (note to self) of the test account
const body = $input.first().json.body || $input.first().json;
const d = body.data || {};
const key = String(body.idempotencyKey || d.id || '');
const chatId = String(d.chatId || d.from || '');
const text = String(d.body || '').trim();
const isGroup = chatId.endsWith('@g.us') || chatId.includes('broadcast') || chatId.includes('status');
const isSelf = SELF_CHATS.includes(chatId);
const phone = isSelf ? OWN : (chatId.endsWith('@c.us') ? chatId.replace(/@c\\.us$/, '').replace(/\\D/g, '') : '');
const sd = $getWorkflowStaticData('global');
sd.seen = sd.seen || [];
const dup = key && sd.seen.includes(key);
if (key) { sd.seen.push(key); if (sd.seen.length > 200) sd.seen = sd.seen.slice(-100); }
let skip = '';
if (body.event && body.event !== 'message.received' && !(body.event === 'message.sent' && isSelf)) skip = 'event ' + body.event;
else if (text.startsWith('🤖')) skip = 'bot message';   // replies of the bot carry this mark: no loops
else if (d.fromMe === true && phone !== OWN) skip = 'outgoing to others';   // only the self chat (test mode) may be fromMe
else if (isGroup) skip = 'group';
else if (!text || (d.type && d.type !== 'chat' && d.type !== 'text')) skip = 'not text';
else if (dup) skip = 'duplicate';
else if (!phone) skip = 'unresolved sender ' + chatId;
else if (!ALLOW.includes(phone)) skip = 'not allowlisted';
return [{ json: { ok: skip === '', skip, phone, chatId, text, key } }];
""".replace('__ALLOW__', json.dumps(ALLOW)).replace('__OWN__', OWN_NUMBER)

webhook = {'id': nid(), 'name': 'OpenWA webhook', 'type': 'n8n-nodes-base.webhook', 'typeVersion': 2.1,
           'position': [0, 200], 'webhookId': nid(),
           'parameters': {'httpMethod': 'POST', 'path': WH_PATH, 'responseMode': 'onReceived', 'options': {}}}
filt = {'id': nid(), 'name': 'Filter message', 'type': 'n8n-nodes-base.code', 'typeVersion': 2, 'position': [224, 200],
        'parameters': {'mode': 'runOnceForAllItems', 'language': 'javaScript', 'jsCode': FILTER_JS},
        'notes': 'Allowlist: only the numbers listed in ALLOW get answers. Empty list = the bot stays silent.'}
gate = if_true('Should answer?', '={{ $json.ok }}', [448, 200])
agent = {'id': nid(), 'name': 'WhatsApp front desk', 'type': '@n8n/n8n-nodes-langchain.agent', 'typeVersion': 3.1,
         'position': [672, 100],
         'parameters': {'promptType': 'define',
                        'text': "=[WhatsApp customer, phone: {{ $json.phone }}]\n{{ $json.text }}",
                        'options': {'systemMessage': sysmsg, 'maxIterations': 10}},
         'onError': 'continueRegularOutput'}
llm = copy.deepcopy(by['Claude (Front desk)'])
llm.update({'name': 'Claude (WhatsApp)', 'id': nid(), 'position': [592, 330]})
mem = {'id': nid(), 'name': 'Memory per phone', 'type': '@n8n/n8n-nodes-langchain.memoryBufferWindow',
       'typeVersion': 1.4, 'position': [720, 330],
       'parameters': {'sessionIdType': 'customKey',
                      'sessionKey': "=wa-{{ $('Filter message').first().json.phone }}",
                      'contextWindowLength': 12}}
tools = []
for nm, x in (('Order agent', 848), ('Support agent', 976), ('Products', 1104)):
    t = copy.deepcopy(by[nm])
    t.update({'id': nid(), 'position': [x, 330]})
    tools.append(t)
PREP_JS = """// Why Code: keeps the agent answer or a safe fallback if the agent failed.
const f = $('Filter message').first().json;
const out = $input.first().json;
let text = String(out.output || '').trim();
const failed = !text || !!out.error;
if (failed) text = 'Disculpa, tuve un problema para responder. Intenta de nuevo en un momento.';
text = '🤖 ' + text;
return [{ json: { chatId: f.chatId, phone: f.phone, text, failed } }];
"""
prep = {'id': nid(), 'name': 'Prepare reply', 'type': 'n8n-nodes-base.code', 'typeVersion': 2, 'position': [1000, 100],
        'parameters': {'mode': 'runOnceForAllItems', 'language': 'javaScript', 'jsCode': PREP_JS}}
send = send_node('Send reply', '$json.chatId', '$json.text', [1224, 100])
logr = log_node('Log reply', 'WhatsApp',
                "={{ $('Prepare reply').first().json.failed ? 'reply_fallback' : 'reply_sent' }}",
                "=wa-{{ $('Prepare reply').first().json.phone }}",
                "={{ $json.error ? 'ERROR enviando: ' + String($json.error.message || $json.error).slice(0, 150) : "
                "'Respuesta enviada (' + String($('Prepare reply').first().json.text).length + ' caracteres)' }}",
                [1448, 100])
logs = log_node('Log ignored', 'WhatsApp', 'message_ignored', "=wa-{{ $json.phone }}", "={{ $json.skip }}", [672, 520])
note = {'id': nid(), 'name': 'Note', 'type': 'n8n-nodes-base.stickyNote', 'typeVersion': 1, 'position': [0, 380],
        'parameters': {'content': "## WhatsApp (OpenWA)\nOpenWA envia cada mensaje a este webhook. Solo responde a los numeros de la lista ALLOW de 'Filter message'. La memoria es por telefono. Las respuestas salen por `send-text` de la sesion `delivery-system`.",
                       'color': 4, 'width': 360, 'height': 180}}
nodes = [webhook, filt, gate, agent, llm, mem] + tools + [prep, send, logr, logs, note]
conn = {
    'OpenWA webhook': {'main': [link('Filter message')]},
    'Filter message': {'main': [link('Should answer?')]},
    'Should answer?': {'main': [link('WhatsApp front desk'), link('Log ignored')]},
    'WhatsApp front desk': {'main': [link('Prepare reply')]},
    'Prepare reply': {'main': [link('Send reply')]},
    'Send reply': {'main': [link('Log reply')]},
    'Claude (WhatsApp)': {'ai_languageModel': [[{'node': 'WhatsApp front desk', 'type': 'ai_languageModel', 'index': 0}]]},
    'Memory per phone': {'ai_memory': [[{'node': 'WhatsApp front desk', 'type': 'ai_memory', 'index': 0}]]},
}
for t in tools:
    conn[t['name']] = {'ai_tool': [[{'node': 'WhatsApp front desk', 'type': 'ai_tool', 'index': 0}]]}
gw = [{'id': 'WhatsAppGate01', 'name': 'Demo Traders - WhatsApp Gateway', 'active': False, 'nodes': nodes,
       'connections': conn,
       'settings': {'executionOrder': 'v1', 'timezone': 'America/Santo_Domingo', 'availableInMCP': True},
       'pinData': {}, 'tags': []}]

# ---------------------------------------------------------------- notify customer
with open(os.path.join(ROOT, 'tools', 'notify-base.json'), encoding='utf-8') as _f:
    nt = json.load(_f)
nn = {n['name']: n for n in nt['nodes']}
PLAN_JS = """// Why Code: email when a valid email exists; WhatsApp (OpenWA) when the phone is on the test allowlist.
const ALLOW = __ALLOW__;   // numbers that may receive WhatsApp messages. Empty = nothing is sent; messages stay as whatsapp_pending.
const t = $input.first().json;
const email = String(t.customer_email || '').trim().toLowerCase();
const hasEmail = /^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$/.test(email);
let phone = String(t.customer_phone || '').replace(/\\D/g, '');
if (phone.length === 10) phone = '1' + phone;   // Dominican numbers without country code
const sendWa = phone.length >= 11 && ALLOW.includes(phone);
return [{ json: { send_email: hasEmail, email: hasEmail ? email : '', phone, has_phone: phone.length >= 7, send_wa: sendWa, wa_pending: !hasEmail && !sendWa, wa_chat: phone + '@c.us', order_id: String(t.order_id || ''), event: String(t.event || ''), subject: String(t.subject || ''), message: String(t.message || ''), name: String(t.customer_name || '') } }];
""".replace('__ALLOW__', json.dumps(ALLOW))
nn['Plan channels']['parameters']['jsCode'] = PLAN_JS
nn['Plan channels']['notes'] = 'Why Code: email when valid; WhatsApp (OpenWA) when the phone is on the test allowlist; otherwise saved as whatsapp_pending.'
nt['nodes'] = [n for n in nt['nodes'] if not n['name'].startswith('Sticky Note')]
nn['Log WhatsApp pending']['position'] = [672, 384]
wa_if = if_true('Send WhatsApp?', '={{ $json.send_wa }}', [448, 192])
pend_if = if_true('Needs pending note?', '={{ $json.wa_pending }}', [448, 384])
wa_send = send_node('Send WhatsApp', '$json.wa_chat', "'🤖 ' + $json.message", [672, 192])
wa_log = log_node('Log WhatsApp result', 'Notify',
                  "={{ $json.error ? 'whatsapp_failed' : 'whatsapp_sent' }}",
                  "={{ $('Plan channels').first().json.order_id }}",
                  "={{ $('Plan channels').first().json.event }}: {{ $json.error ? 'ERROR WhatsApp ' + String($json.error.message || $json.error).slice(0, 120) : 'WhatsApp enviado a ' + $('Plan channels').first().json.phone }}",
                  [896, 192])
nt['nodes'] += [wa_if, pend_if, wa_send, wa_log]
c = nt['connections']
c['Plan channels'] = {'main': [link('Has email?', 'Send WhatsApp?', 'Needs pending note?')]}
c['Has email?'] = {'main': [link('Send email'), []]}
c['Send WhatsApp?'] = {'main': [link('Send WhatsApp'), []]}
c['Send WhatsApp'] = {'main': [link('Log WhatsApp result')]}
c['Needs pending note?'] = {'main': [link('Log WhatsApp pending'), []]}
for k in ('versionId', 'activeVersionId', 'sourceWorkflowId', 'versionMetadata', 'updatedAt', 'createdAt'):
    nt.pop(k, None)
nt['active'] = False
nt['settings'] = dict(nt.get('settings') or {}, availableInMCP=True)

os.makedirs(OUT, exist_ok=True)
for fn, wf in (('12-whatsapp-gateway.json', gw), ('10-notify-customer.json', [nt])):
    with open(os.path.join(OUT, fn), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(wf, f, ensure_ascii=False, indent=2)
print('allowlist size', len(ALLOW), '->', OUT)
