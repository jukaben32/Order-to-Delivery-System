# Inventario y contabilidad

Cómo el sistema lleva el inventario y qué deja listo para la contabilidad.

## Principio

Cada vez que cambia el stock de un producto, el cambio queda escrito en el **kardex** (la pestaña `Inventory_Movements`) con su tipo, cantidad, saldo, costo y referencia. El stock de la hoja `Products` es siempre el resultado de esos movimientos.

## Kardex: `Inventory_Movements`

| Columna | Qué guarda |
|---|---|
| `Movement_ID` | Número único (`MOV-aaaammddHHmmss-…`) |
| `Time` | Fecha y hora |
| `SKU`, `Product` | Producto |
| `Type` | Tipo de movimiento (tabla de abajo) |
| `Qty` | Cantidad con signo: positiva si entra, negativa si sale |
| `Stock_After` | Stock del producto después del movimiento |
| `Unit_Cost` | Costo unitario en ese momento |
| `Value` | `Qty` × `Unit_Cost` (con signo) |
| `Ref_ID` | Pedido o solicitud de compra relacionada |
| `Notes`, `Source` | Motivo y de dónde vino (pedido, formulario…) |

| Tipo | Cuándo se genera | Efecto en el stock |
|---|---|---|
| `SALE` | Al confirmar un pedido (tienda o chat) | Baja |
| `CANCEL_RETURN` | Al cancelar un pedido | Sube |
| `PURCHASE_RECEIPT` | Entrada de mercancía (compra) | Sube, y recalcula el costo |
| `CUSTOMER_RETURN` | Devolución de un cliente | Sube |
| `ADJUST_UP` / `ADJUST_DOWN` | Ajuste por conteo físico | Sube / baja |
| `SHRINKAGE` | Merma (dañado o vencido) | Baja |

> **Cuándo baja el inventario:** al **confirmar** el pedido, no cuando sale ni cuando se entrega. Marcar una entrega no mueve el stock. Es una reserva en el momento de la venta, para no vender dos veces lo mismo.

## Costo y valor del inventario

`Products` tiene la columna `Cost` (costo unitario). Al recibir mercancía con un costo, el sistema calcula el **costo promedio ponderado**:

```
nuevo costo = (stock actual × costo actual + cantidad recibida × costo nuevo) / (stock actual + cantidad recibida)
```

- **Valor del inventario** = suma de `Stock` × `Cost` de todos los productos.
- **Costo de ventas** = valor de las salidas por ventas, menos lo devuelto por cancelaciones y devoluciones.
- **Margen bruto** = ventas − costo de ventas.

Los costos que trae el flujo `Seed Data` son de ejemplo (72 % del precio). Cámbialos por los reales en `Products`.

## Formularios del personal (con contraseña)

| Formulario | Ruta | Qué hace |
|---|---|---|
| Movimiento de inventario | `/form/demo-traders-stock-movement` | Entradas de mercancía, devoluciones, ajustes por conteo y mermas. Nunca deja el stock en negativo. Una entrada ligada a una solicitud de compra la marca `Partial` o `Received` según lo recibido en total. |
| Cancelar pedido | `/form/demo-traders-cancel-order` | Devuelve el stock, cancela la factura, libera al repartidor si ya había salido y avisa al cliente. Rechaza pedidos ya entregados o ya cancelados. |
| Record payment | `/form/demo-traders-record-payment` | Pagos. Rechaza facturas canceladas. |
| Mark delivered | `/form/demo-traders-mark-delivered` | Entregas. |

**Facturas pagadas y luego canceladas:** la factura pasa a `Refund pending` (devolución pendiente), el sistema no devuelve dinero por sí solo, y el informe del dueño lo avisa.

## Informe diario del dueño

Lo calcula un nodo Code con los datos del Sheet; la IA solo redacta el correo. Incluye:

- Ventas del día, pedidos cancelados.
- **Resumen contable**: cobros del día, costo de ventas, margen bruto, compras recibidas y ajustes de inventario.
- **Inventario**: valor total y productos con stock bajo.
- **Cuentas por cobrar**: total y lista de facturas con saldo, con las vencidas.
- Devoluciones de dinero pendientes.
- Pedidos sin despachar, entregas tardías y pedidos esperando repartidor.

## Para el contador

Todo está en el Google Sheet y se puede exportar a Excel o CSV:

| Necesidad | Pestaña |
|---|---|
| Ventas | `Orders` (filtrar `Status` distinto de `Cancelled`) y `Invoices` |
| Cobros | `Payments` |
| Cuentas por cobrar | `Invoices` con `Status` `Unpaid` o `Partial` |
| Compras | `Inventory_Movements` con `Type = PURCHASE_RECEIPT` |
| Costo de ventas | `Inventory_Movements` con `Type = SALE` o `CANCEL_RETURN` |
| Mermas y ajustes | `Inventory_Movements` con `Type = SHRINKAGE` o `ADJUST_*` |
| Historial de todo | `Activity_Log` |

## Limitaciones

- **No hay impuestos** (ITBIS) ni comprobantes fiscales (NCF): las facturas son internas. Para facturar legalmente hace falta integrar un sistema autorizado.
- **Sin devolución de dinero automática**: las facturas pagadas y canceladas quedan marcadas para que alguien devuelva el dinero.
- **Cancelar un pedido ya despachado** libera al repartidor y devuelve el stock de inmediato, pero un pedido que esperaba repartidor no se asigna solo hasta la próxima entrega.
- **Sheets no es una base de datos transaccional**: dos pedidos en el mismo segundo pueden leer el mismo stock. Con más volumen conviene pasar a una base de datos real.
