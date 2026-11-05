import sys
sys.path.insert(0, sys.argv[1])
from n8nbuild import *

NOTIFY_ID = sys.argv[3]
MOVE_COLS = ['Movement_ID', 'Time', 'SKU', 'Product', 'Type', 'Qty', 'Stock_After', 'Unit_Cost', 'Value', 'Ref_ID', 'Notes', 'Source']
PRODUCT_STOCK_COLS = ['SKU', 'Stock', 'Cost']

w = Wf('InvControlDemo01', 'Demo Traders - Inventory Control')

# =====================================================================
# A) STOCK MOVEMENT FORM: purchases received, customer returns, count adjustments, shrinkage
# =====================================================================
form_a = w.add(form_trigger(
    'Stock movement form', 'Movimiento de inventario',
    'Solo personal. Registra entradas de mercancia, devoluciones, ajustes por conteo y mermas. Cada movimiento queda en el kardex (Inventory_Movements).',
    [
        {'fieldLabel': 'Tipo de movimiento', 'fieldType': 'dropdown', 'requiredField': True,
         'fieldOptions': {'values': [{'option': 'Entrada de mercancía (compra)'}, {'option': 'Devolución de cliente'},
                                     {'option': 'Ajuste por conteo: sobrante'}, {'option': 'Ajuste por conteo: faltante'},
                                     {'option': 'Merma (dañado o vencido)'}]}},
        {'fieldLabel': 'SKU', 'fieldType': 'text', 'placeholder': 'RICE-5KG', 'requiredField': True},
        {'fieldLabel': 'Cantidad', 'fieldType': 'number', 'requiredField': True},
        {'fieldLabel': 'Costo unitario', 'fieldType': 'number', 'placeholder': 'Solo en entradas de mercancia', 'requiredField': False},
        {'fieldLabel': 'Referencia', 'fieldType': 'text', 'placeholder': 'PR-... (solicitud de compra) o ORD-...', 'requiredField': False},
        {'fieldLabel': 'Notas', 'fieldType': 'text', 'requiredField': False},
    ], 'demo-traders-stock-movement'))

rp_a = w.add(sheet_read('Read products for movement', 'Products', always=True))
rpr_a = w.add(sheet_read('Read purchase requests', 'Purchase_Requests', always=True, once=True))
rmv_a = w.add(sheet_read('Read movements for movement', 'Inventory_Movements', always=True, once=True))

plan_a = w.add(code('Plan stock movement', r'''const form = $('Stock movement form').first().json;
const products = $('Read products for movement').all().map(function (i) { return i.json; }).filter(function (p) { return p.SKU; });
const prs = $('Read purchase requests').all().map(function (i) { return i.json; }).filter(function (r) { return r.PR_ID; });
const moves = $input.all().map(function (i) { return i.json; }).filter(function (m) { return m.Movement_ID; });
function fail(msg) { return [{ json: { ok: false, message: msg } }]; }
const TYPES = {
  'Entrada de mercancía (compra)': { code: 'PURCHASE_RECEIPT', sign: 1 },
  'Devolución de cliente': { code: 'CUSTOMER_RETURN', sign: 1 },
  'Ajuste por conteo: sobrante': { code: 'ADJUST_UP', sign: 1 },
  'Ajuste por conteo: faltante': { code: 'ADJUST_DOWN', sign: -1 },
  'Merma (dañado o vencido)': { code: 'SHRINKAGE', sign: -1 }
};
const t = TYPES[String(form['Tipo de movimiento'] || '')];
const sku = String(form['SKU'] || '').trim().toUpperCase();
const qty = Math.round(Number(form['Cantidad']));
const ref = String(form['Referencia'] || '').trim();
const notes = String(form['Notas'] || '').trim().slice(0, 200);
if (!t) { return fail('Elige un tipo de movimiento.'); }
const p = products.find(function (x) { return String(x.SKU).toUpperCase() === sku; });
if (!p) { return fail('El producto ' + sku + ' no existe en el catálogo. No se registró nada.'); }
if (!(qty > 0)) { return fail('La cantidad debe ser mayor que cero. No se registró nada.'); }
const stock = Number(p.Stock) || 0;
const oldCost = Number(p.Cost) || 0;
const delta = t.sign * qty;
const newStock = stock + delta;
if (newStock < 0) { return fail('No se puede: el stock de ' + p.Name + ' es ' + stock + ' y quedaría en ' + newStock + '. No se registró nada.'); }
let unitCost = oldCost;
let newCost = oldCost;
const costIn = Number(form['Costo unitario']);
if (t.code === 'PURCHASE_RECEIPT' && costIn > 0) {
  unitCost = costIn;
  newCost = Math.round(((stock * oldCost + qty * costIn) / (stock + qty)) * 100) / 100;
}
let prId = '';
let prStatus = '';
if (t.code === 'PURCHASE_RECEIPT' && ref) {
  const pr = prs.find(function (r) { return String(r.PR_ID).toUpperCase() === ref.toUpperCase(); });
  if (!pr) { return fail('La solicitud de compra ' + ref + ' no existe. Déjala vacía si no aplica. No se registró nada.'); }
  if (String(pr.SKU).toUpperCase() !== sku) { return fail('La solicitud ' + pr.PR_ID + ' es de ' + pr.SKU + ', no de ' + sku + '. No se registró nada.'); }
  const before = moves.filter(function (m) { return String(m.Type) === 'PURCHASE_RECEIPT' && String(m.Ref_ID).toUpperCase() === ref.toUpperCase(); }).reduce(function (s, m) { return s + (Number(m.Qty) || 0); }, 0);
  prId = pr.PR_ID;
  prStatus = (before + qty) >= Number(pr.Qty) ? 'Received' : 'Partial';
}
const value = Math.round(delta * unitCost * 100) / 100;
const label = { PURCHASE_RECEIPT: 'Entrada de mercancía', CUSTOMER_RETURN: 'Devolución de cliente', ADJUST_UP: 'Ajuste (sobrante)', ADJUST_DOWN: 'Ajuste (faltante)', SHRINKAGE: 'Merma' }[t.code];
let message = label + ' registrada: ' + p.Name + ' ' + (delta > 0 ? '+' : '') + delta + '. Stock: ' + stock + ' → ' + newStock + '.';
if (t.code === 'PURCHASE_RECEIPT' && costIn > 0) { message += ' Costo promedio: RD$ ' + newCost + '.'; }
if (prId) { message += ' Solicitud ' + prId + ': ' + (prStatus === 'Received' ? 'recibida completa' : 'recibida parcial') + '.'; }
return [{ json: { ok: true, SKU: String(p.SKU), product: p.Name, code: t.code, qty: delta, new_stock: newStock, unit_cost: unitCost, new_cost: newCost, value: value, ref: ref, notes: notes, pr_id: prId, pr_status: prStatus, movement_id: 'MOV-' + $now.toFormat('yyyyMMddHHmmss') + '-' + Math.floor(100 + Math.random() * 900), message: message } }];''',
    'Why Code: validates the movement (existing SKU, positive quantity, stock never below zero), computes the weighted average cost for purchase receipts and decides if a purchase request is fully or partially received.'))

ok_a = w.add(if_bool('Movement valid?', '={{ $json.ok }}'))

upd_prod_a = w.add(sheet_update('Update product stock and cost', 'Products', 'SKU', PRODUCT_STOCK_COLS, {
    'SKU': '={{ $json.SKU }}', 'Stock': '={{ $json.new_stock }}', 'Cost': '={{ $json.new_cost }}'}))

def movement_values(ref):
    return {
        'Movement_ID': '={{ %s.movement_id }}' % ref,
        'Time': '={{ $now.toFormat("yyyy-MM-dd HH:mm:ss") }}',
        'SKU': '={{ %s.SKU }}' % ref,
        'Product': '={{ %s.product }}' % ref,
        'Type': '={{ %s.code }}' % ref,
        'Qty': '={{ %s.qty }}' % ref,
        'Stock_After': '={{ %s.new_stock }}' % ref,
        'Unit_Cost': '={{ %s.unit_cost }}' % ref,
        'Value': '={{ %s.value }}' % ref,
        'Ref_ID': '={{ %s.ref }}' % ref,
        'Notes': '={{ %s.notes }}' % ref,
        'Source': 'Stock movement form'}

PA = '$("Plan stock movement").first().json'
save_mv_a = w.add(sheet_append('Save movement', 'Inventory_Movements', MOVE_COLS, movement_values(PA)))
has_pr = w.add(if_bool('Linked purchase request?', '={{ !!%s.pr_id }}' % PA))
upd_pr = w.add(sheet_update('Update purchase request', 'Purchase_Requests', 'PR_ID', ['PR_ID', 'Status'], {
    'PR_ID': '={{ %s.pr_id }}' % PA, 'Status': '={{ %s.pr_status }}' % PA}))
log_a = w.add(log_node('Log stock movement', 'Inventory', '={{ "stock_" + %s.code.toLowerCase() }}' % PA,
                       '={{ %s.movement_id }}' % PA, '={{ %s.message }}' % PA))
done_a = w.add(form_done('Movement recorded page', 'Movimiento registrado', '={{ %s.message }}' % PA))
log_rej_a = w.add(log_node('Log rejected movement', 'Inventory', 'stock_movement_rejected', '', '={{ $json.message }}'))
rej_a = w.add(form_done('Movement rejected page', 'Movimiento no registrado', '={{ $("Plan stock movement").first().json.message }}'))

w.chain(form_a, rp_a, rpr_a, rmv_a, plan_a, ok_a)
w.link(ok_a, upd_prod_a, 0)
w.chain(upd_prod_a, save_mv_a, has_pr)
w.link(has_pr, upd_pr, 0)
w.link(upd_pr, log_a)
w.link(has_pr, log_a, 1)
w.link(log_a, done_a)
w.link(ok_a, log_rej_a, 1)
w.link(log_rej_a, rej_a)

# =====================================================================
# B) CANCEL ORDER FORM: restocks, cancels the invoice, frees the rider, notifies the customer
# =====================================================================
form_b = w.add(form_trigger(
    'Cancel order form', 'Cancelar pedido',
    'Solo personal. Cancela un pedido que no se ha entregado: devuelve el stock, cancela la factura, libera al repartidor y avisa al cliente.',
    [
        {'fieldLabel': 'Pedido', 'fieldType': 'text', 'placeholder': 'ORD-1001', 'requiredField': True},
        {'fieldLabel': 'Motivo', 'fieldType': 'dropdown', 'requiredField': True,
         'fieldOptions': {'values': [{'option': 'Cliente canceló'}, {'option': 'Producto no disponible'},
                                     {'option': 'Error en el pedido'}, {'option': 'Otro'}]}},
    ], 'demo-traders-cancel-order'))

r_orders = w.add(sheet_read('Read orders for cancel', 'Orders', always=True))
r_inv = w.add(sheet_read('Read invoices for cancel', 'Invoices', always=True, once=True))
r_disp = w.add(sheet_read('Read dispatch for cancel', 'Dispatch', always=True, once=True))
r_staff = w.add(sheet_read('Read staff for cancel', 'Staff', always=True, once=True))
r_cust = w.add(sheet_read('Read customers for cancel', 'Customers', always=True, once=True))
r_prod = w.add(sheet_read('Read products for cancel', 'Products', always=True, once=True))

plan_b = w.add(code('Plan cancellation', r'''const form = $('Cancel order form').first().json;
const wanted = String(form['Pedido'] || '').trim().toUpperCase();
const reason = String(form['Motivo'] || 'Otro');
function rows(n) { return $(n).all().map(function (i) { return i.json; }); }
function fail(m) { return [{ json: { ok: false, message: m } }]; }
const order = rows('Read orders for cancel').find(function (o) { return String(o.Order_ID || '').toUpperCase() === wanted; });
if (!order) { return fail('No encontré el pedido ' + wanted + '. No se cambió nada.'); }
const status = String(order.Status);
if (status === 'Cancelled') { return fail('El pedido ' + order.Order_ID + ' ya estaba cancelado. No se cambió nada.'); }
if (status === 'Delivered') { return fail('El pedido ' + order.Order_ID + ' ya fue entregado. Para una devolución usa el formulario de movimiento de inventario (Devolución de cliente). No se cambió nada.'); }
const inv = rows('Read invoices for cancel').find(function (i) { return String(i.Order_ID) === String(order.Order_ID); });
const disp = rows('Read dispatch for cancel').find(function (d) { return String(d.Order_ID) === String(order.Order_ID) && String(d.Status) === 'Dispatched'; });
const staff = disp ? rows('Read staff for cancel').find(function (s) { return String(s.Name) === String(disp.Rider); }) : null;
const cust = rows('Read customers for cancel').find(function (c) { return String(c.Customer_ID) === String(order.Customer_ID); }) || {};
const products = rows('Read products for cancel').filter(function (p) { return p.SKU; });
const items = String(order.Items || '').split(';').map(function (s) { return s.trim(); }).filter(Boolean).map(function (s) {
  const m = s.match(/^(.+?)\s*x\s*(\d+)$/);
  return m ? { sku: m[1].trim(), qty: Number(m[2]) } : null;
}).filter(Boolean);
const stamp = $now.toFormat('yyyyMMddHHmmss');
const restock = [];
items.forEach(function (it, idx) {
  const p = products.find(function (x) { return String(x.SKU) === it.sku; });
  if (!p) { return; }
  const stock = Number(p.Stock) || 0;
  const cost = Number(p.Cost) || 0;
  restock.push({ SKU: it.sku, product: p.Name, qty: it.qty, new_stock: stock + it.qty, unit_cost: cost, value: Math.round(it.qty * cost * 100) / 100, movement_id: 'MOV-' + stamp + '-' + (idx + 1), notes: reason });
});
if (!restock.length) { return fail('No pude leer los productos del pedido ' + order.Order_ID + '. No se cambió nada.'); }
const hasInvoice = !!inv;
const refund = hasInvoice && String(inv.Status) !== 'Unpaid';
const invoiceNew = hasInvoice ? (refund ? 'Refund pending' : 'Cancelled') : '';
let message = 'Pedido ' + order.Order_ID + ' cancelado (' + reason + '). Stock devuelto: ' + restock.map(function (r) { return r.qty + ' x ' + r.SKU; }).join(', ') + '.';
if (hasInvoice) { message += ' Factura ' + inv.Invoice_No + ': ' + invoiceNew + '.'; }
if (refund) { message += ' ATENCIÓN: la factura tenía pagos registrados; hay que devolver el dinero al cliente.'; }
if (disp) { message += ' ' + disp.Rider + ' queda libre: confirma que regrese la mercancía.'; }
return [{ json: { ok: true, order_id: order.Order_ID, reason: reason, restock: restock, has_invoice: hasInvoice, invoice_no: hasInvoice ? inv.Invoice_No : '', invoice_new_status: invoiceNew, refund_pending: refund, has_dispatch: !!disp, dispatch_id: disp ? disp.Dispatch_ID : '', staff_id: staff ? staff.Staff_ID : '', rider_name: disp ? disp.Rider : '', customer_name: String(cust.Name || ''), customer_email: String(cust.Email || ''), customer_phone: String(cust.Phone || ''), message: message } }];''',
    'Why Code: finds the order, its invoice, open delivery, rider and customer; parses the items of the order and works out the new stock of each product. Delivered or already cancelled orders are rejected.'))

ok_b = w.add(if_bool('Cancellable?', '={{ $json.ok }}'))
split_b = w.add(code('Split restock lines', "return $input.first().json.restock.map(function (r) { return { json: r }; });",
                     'Why Code: turns the restock array into one item per product so the Sheets nodes update each product.'))
upd_stock_b = w.add(sheet_update('Return stock', 'Products', 'SKU', ['SKU', 'Stock'], {
    'SKU': '={{ $json.SKU }}', 'Stock': '={{ $json.new_stock }}'}))

SB = '$("Split restock lines").item.json'
mv_b_values = {
    'Movement_ID': '={{ %s.movement_id }}' % SB,
    'Time': '={{ $now.toFormat("yyyy-MM-dd HH:mm:ss") }}',
    'SKU': '={{ %s.SKU }}' % SB,
    'Product': '={{ %s.product }}' % SB,
    'Type': 'CANCEL_RETURN',
    'Qty': '={{ %s.qty }}' % SB,
    'Stock_After': '={{ %s.new_stock }}' % SB,
    'Unit_Cost': '={{ %s.unit_cost }}' % SB,
    'Value': '={{ %s.value }}' % SB,
    'Ref_ID': '={{ $("Plan cancellation").first().json.order_id }}',
    'Notes': '={{ %s.notes }}' % SB,
    'Source': 'Cancel order form'}
save_mv_b = w.add(sheet_append('Save return movements', 'Inventory_Movements', MOVE_COLS, mv_b_values))
back_b = w.add(code('Back to one item', "return [{ json: $('Plan cancellation').first().json }];",
                    'Why Code: after the per-product updates, continues with one item carrying the cancellation plan.'))
PB = '$("Plan cancellation").first().json'
cancel_row = w.add(sheet_update('Mark order cancelled', 'Orders', 'Order_ID', ['Order_ID', 'Status'], {
    'Order_ID': '={{ %s.order_id }}' % PB, 'Status': 'Cancelled'}))
has_inv = w.add(if_bool('Has invoice?', '={{ %s.has_invoice }}' % PB))
cancel_inv = w.add(sheet_update('Cancel invoice', 'Invoices', 'Invoice_No', ['Invoice_No', 'Status'], {
    'Invoice_No': '={{ %s.invoice_no }}' % PB, 'Status': '={{ %s.invoice_new_status }}' % PB}))
has_disp = w.add(if_bool('Has open delivery?', '={{ %s.has_dispatch }}' % PB))
cancel_disp = w.add(sheet_update('Cancel dispatch row', 'Dispatch', 'Dispatch_ID', ['Dispatch_ID', 'Status'], {
    'Dispatch_ID': '={{ %s.dispatch_id }}' % PB, 'Status': 'Cancelled'}))
free_rider = w.add(sheet_update('Free rider', 'Staff', 'Staff_ID', ['Staff_ID', 'Available'], {
    'Staff_ID': '={{ %s.staff_id }}' % PB, 'Available': 'Yes'}))
notify_b = w.add(notify_call(
    'Notify cancelled', NOTIFY_ID, PB, 'cancelled',
    '=Tu pedido {{ %s.order_id }} fue cancelado' % PB,
    '=Hola {{ %s.customer_name }}, tu pedido {{ %s.order_id }} fue cancelado. {{ %s.refund_pending ? "Como ya tenías un pago registrado, nos comunicaremos contigo para devolverte tu dinero. " : "" }}Si tienes alguna duda, responde este mensaje.\n\nDemo Traders' % (PB, PB, PB)))
log_b = w.add(log_node('Log cancellation', 'Inventory', 'order_cancelled', '={{ %s.order_id }}' % PB, '={{ %s.message }}' % PB))
done_b = w.add(form_done('Order cancelled page', 'Pedido cancelado', '={{ %s.message }}' % PB))
log_rej_b = w.add(log_node('Log rejected cancellation', 'Inventory', 'cancellation_rejected', '', '={{ $json.message }}'))
rej_b = w.add(form_done('Cancellation rejected page', 'No se canceló', '={{ $("Plan cancellation").first().json.message }}'))

w.chain(form_b, r_orders, r_inv, r_disp, r_staff, r_cust, r_prod, plan_b, ok_b)
w.link(ok_b, split_b, 0)
w.chain(split_b, upd_stock_b, save_mv_b, back_b, cancel_row, has_inv)
w.link(has_inv, cancel_inv, 0)
w.link(cancel_inv, has_disp)
w.link(has_inv, has_disp, 1)
w.link(has_disp, cancel_disp, 0)
w.chain(cancel_disp, free_rider, notify_b)
w.link(has_disp, notify_b, 1)
w.chain(notify_b, log_b, done_b)
w.link(ok_b, log_rej_b, 1)
w.link(log_rej_b, rej_b)

w.save(sys.argv[2])
