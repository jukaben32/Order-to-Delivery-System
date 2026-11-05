import json
import sys
import uuid

html_path = sys.argv[1]
out_path = sys.argv[2]
create_order_id = sys.argv[3]

html = open(html_path, encoding='utf-8').read()
assert '{{' not in html, 'HTML contains an n8n expression marker'

SHEETS = {'googleSheetsOAuth2Api': {'id': 'uVqG7fQd8cxSfaMU', 'name': 'order to delivery system'}}
DOC = {'__rl': True, 'mode': 'id', 'value': '1uFc0RmztEiY9tcsNGLe0bExBuhJ5Zxjp6j-J7WfYYjc'}


def nid():
    return str(uuid.uuid4())


def webhook(name, path, method, pos):
    return {'id': nid(), 'name': name, 'type': 'n8n-nodes-base.webhook', 'typeVersion': 2.2, 'position': pos,
            'webhookId': nid(),
            'parameters': {'httpMethod': method, 'path': path, 'responseMode': 'responseNode', 'options': {}}}


def respond_json(name, body, pos, code=None):
    opts = {}
    if code is not None:
        opts['responseCode'] = code
    return {'id': nid(), 'name': name, 'type': 'n8n-nodes-base.respondToWebhook', 'typeVersion': 1.5, 'position': pos,
            'parameters': {'respondWith': 'json', 'responseBody': body, 'options': opts}}


def code(name, js, pos, notes=None):
    n = {'id': nid(), 'name': name, 'type': 'n8n-nodes-base.code', 'typeVersion': 2, 'position': pos,
         'parameters': {'mode': 'runOnceForAllItems', 'language': 'javaScript', 'jsCode': js}}
    if notes:
        n['notes'] = notes
    return n


def if_bool(name, left, pos):
    return {'id': nid(), 'name': name, 'type': 'n8n-nodes-base.if', 'typeVersion': 2.4, 'position': pos,
            'parameters': {'conditions': {'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'strict'},
                                          'conditions': [{'id': nid(), 'leftValue': left, 'rightValue': '',
                                                          'operator': {'type': 'boolean', 'operation': 'true', 'singleValue': True}}],
                                          'combinator': 'and'}, 'options': {}}}


nodes = []

# --- the page ---
nodes.append(webhook('Store page', 'tienda', 'GET', [0, 0]))
nodes.append({'id': nid(), 'name': 'Send store page', 'type': 'n8n-nodes-base.respondToWebhook', 'typeVersion': 1.5,
              'position': [260, 0],
              'notes': 'Serves the storefront HTML (source file: storefront/index.html).',
              'parameters': {'respondWith': 'text', 'responseBody': html,
                             'options': {'responseCode': 200, 'responseHeaders': {'entries': [
                                 {'name': 'Content-Type', 'value': 'text/html; charset=utf-8'},
                                 {'name': 'Cache-Control', 'value': 'no-cache'}]}}}})

# --- products API with a 60 second cache (protects the Google Sheets quota) ---
nodes.append(webhook('Products API', 'tienda-api/productos', 'GET', [0, 300]))
nodes.append(code('Check cache',
                  "const cache = $getWorkflowStaticData('global');\n"
                  "const now = Date.now();\n"
                  "if (cache.products && cache.at && (now - cache.at) < 60000) {\n"
                  "  return [{ json: { fresh: true, products: cache.products } }];\n"
                  "}\n"
                  "return [{ json: { fresh: false } }];",
                  [260, 300],
                  'Why Code: keeps the product list for 60 seconds in workflow static data so many visitors do not exhaust the Google Sheets read quota (60 per minute).'))
nodes.append(if_bool('Cache fresh?', '={{ $json.fresh }}', [520, 300]))
nodes.append(respond_json('Send cached products', '={{ { "products": $json.products } }}', [800, 220]))
nodes.append({'id': nid(), 'name': 'Read products', 'type': 'n8n-nodes-base.googleSheets', 'typeVersion': 4.7,
              'position': [800, 400], 'alwaysOutputData': True, 'retryOnFail': True, 'maxTries': 5, 'waitBetweenTries': 5000,
              'credentials': SHEETS,
              'parameters': {'resource': 'sheet', 'operation': 'read', 'documentId': DOC,
                             'sheetName': {'__rl': True, 'mode': 'name', 'value': 'Products'}}})
nodes.append(code('Shape and cache',
                  "const rows = $input.all().map(function (i) { return i.json; }).filter(function (p) { return p.SKU; });\n"
                  "const products = rows.map(function (p) {\n"
                  "  return { sku: String(p.SKU), name: p.Name, category: p.Category, unit: p.Unit, price: Number(p.Price) || 0, stock: Number(p.Stock) || 0 };\n"
                  "});\n"
                  "const cache = $getWorkflowStaticData('global');\n"
                  "cache.products = products;\n"
                  "cache.at = Date.now();\n"
                  "return [{ json: { products: products } }];",
                  [1060, 400],
                  'Why Code: exposes only public fields (no supplier email, no reorder level) and stores the list in the cache.'))
nodes.append(respond_json('Send fresh products', '={{ { "products": $json.products } }}', [1320, 400]))

# --- order API ---
nodes.append(webhook('Order API', 'tienda-api/pedido', 'POST', [0, 700]))
nodes.append(code('Check request',
                  "const b = $json.body || {};\n"
                  "if (b.website) { return [{ json: { bot: true } }]; }\n"
                  "return [{ json: { bot: false, customer: (b.customer && typeof b.customer === 'object') ? b.customer : {}, items: Array.isArray(b.items) ? b.items : [], payment_method: 'cash_on_delivery', channel: 'Web' } }];",
                  [260, 700],
                  'Why Code: drops requests that fill the hidden honeypot field and keeps only the fields the order needs. The payment method is forced to cash on delivery until card and transfer are enabled.'))
nodes.append(if_bool('Looks human?', '={{ !$json.bot }}', [520, 700]))
nodes.append({'id': nid(), 'name': 'Run Create Order', 'type': 'n8n-nodes-base.executeWorkflow', 'typeVersion': 1.4,
              'position': [800, 640],
              'parameters': {'source': 'database',
                             'workflowId': {'__rl': True, 'mode': 'id', 'value': create_order_id, 'cachedResultName': 'Demo Traders - Create Order'},
                             'mode': 'once', 'options': {'waitForSubWorkflow': True}}})
nodes.append(respond_json('Send order result', '={{ $json }}', [1060, 640], code='={{ $json.ok ? 200 : 422 }}'))
nodes.append(respond_json('Send blocked', '={{ { "ok": false, "errors": ["Solicitud no válida."] } }}', [800, 800], code=400))


def link(a, b, out=0):
    return (a, b, out)


links = [
    link('Store page', 'Send store page'),
    link('Products API', 'Check cache'),
    link('Check cache', 'Cache fresh?'),
    link('Cache fresh?', 'Send cached products', 0),
    link('Cache fresh?', 'Read products', 1),
    link('Read products', 'Shape and cache'),
    link('Shape and cache', 'Send fresh products'),
    link('Order API', 'Check request'),
    link('Check request', 'Looks human?'),
    link('Looks human?', 'Run Create Order', 0),
    link('Looks human?', 'Send blocked', 1),
    link('Run Create Order', 'Send order result'),
]
connections = {}
for a, b, out in links:
    conn = connections.setdefault(a, {'main': []})
    while len(conn['main']) <= out:
        conn['main'].append([])
    conn['main'][out].append({'node': b, 'type': 'main', 'index': 0})

wf = {
    'id': 'StoreFrontDemo01',
    'name': 'Demo Traders - Storefront',
    'active': False,
    'nodes': nodes,
    'connections': connections,
    'settings': {'executionOrder': 'v1', 'timezone': 'America/Santo_Domingo', 'availableInMCP': True},
    'pinData': {},
    'tags': []
}
with open(out_path, 'w', encoding='utf-8', newline='\n') as f:
    json.dump([wf], f, ensure_ascii=False, indent=2)
print('workflow json:', out_path, 'nodes:', len(nodes))
