# Pruebas de punta a punta

Se probó el sistema completo con Google Sheets, Gmail y Claude reales (4 de noviembre de 2026, hora de Santo Domingo).

| # | Prueba | Resultado |
|---|---|---|
| 1 | El chat pide los datos que faltan (nombre, teléfono, correo, dirección) | Pasa |
| 2 | Resumen con total calculado por código: 2 arroz + 1 aceite = RD$ 6,100 | Pasa |
| 3 | Confirmación crea el pedido y guarda al cliente en `Customers` | Pasa |
| 4 | El stock baja (arroz 40→38, aceite 30→29) | Pasa |
| 5 | Stock bajo el mínimo: solicitud de compra de 4 × `Reorder_Level` y correo al proveedor | Pasa |
| 6 | Factura `INV-1001`, vencimiento a 7 días, estado `Unpaid`, correo al cliente | Pasa |
| 7 | Primer repartidor libre asignado y marcado como ocupado | Pasa |
| 8 | Sin repartidores libres: el pedido espera y queda en `Activity_Log` | Pasa |
| 9 | Formulario "Mark delivered": entrega registrada y repartidor libre otra vez | Pasa |
| 10 | Formulario "Record payment": pago registrado y factura en `Paid` | Pasa |
| 11 | Pago a una factura inexistente: se rechaza y se registra | Pasa |
| 12 | Consulta de estado por el chat ("¿dónde está ORD-1001?") | Pasa |
| 13 | Precio por el chat, leído de `Products` | Pasa |
| 14 | Informe del dueño con cifras calculadas por código | Pasa |
| 15 | Los tres formularios devuelven 401 sin contraseña y 200 con ella | Pasa |
| 16 | Conversación completa de 3 mensajes con memoria, hasta el pedido confirmado | Pasa |
| 17 | Los 7 agentes escriben en `Activity_Log` | Pasa |
| 18 | Al entregar un pedido, el pedido en espera más antiguo se asigna al repartidor libre | Pasa |
| 19 | La tienda sirve la página (200) y la API devuelve 50 productos solo con campos públicos | Pasa |
| 20 | Pedido web con datos y carrito vacíos: se rechaza con 422 y 5 mensajes de error | Pasa |
| 21 | Pedido web con el campo trampa lleno: se descarta con 400 | Pasa |
| 22 | Pedido web con un producto inexistente y una cantidad sobre el stock: 422 | Pasa |
| 23 | Pedido web real: 2 cebollas + 1 sal = RD$ 340, pedido ORD-1006, factura INV-1006, entrega en espera | Pasa |
| 24 | Capturas de la tienda: catálogo, carrito, validación del pago, confirmación y vista de 500 px | Pasa |
| 25 | Pedido web **sin correo** de un cliente nuevo: ORD-1008 por RD$ 320, factura INV-1008, `contact_via: whatsapp` | Pasa |
| 26 | El aviso de la factura sin correo no intenta enviar correo y queda como `whatsapp_pending` con el teléfono y el texto | Pasa |
| 27 | Cliente con correo: el aviso de "entregado" (ORD-1003) y el de "en camino" (ORD-1006) llegan por Gmail, en español | Pasa |
| 28 | Chat sin dar correo: el agente no lo pide, muestra el resumen (RD$ 1,435) y confirma el pedido ORD-1009 | Pasa |
| 29 | Correo con formato inválido en la tienda: error claro y "puedes dejarlo vacío" | Pasa |
| 30 | Los tres botones de la cabecera abren su ventana de información (captura de WhatsApp y entrega) | Pasa |
| 31 | Una venta (2 cebollas + 1 sal) deja 2 filas `SALE` en el kardex con cantidad negativa, saldo y costo unitario (50 y 144) | Pasa |
| 32 | Entrada de mercancía parcial ligada a una solicitud de compra: stock 4 → 16, costo promedio RD$ 975, solicitud en `Partial` | Pasa |
| 33 | Segunda entrega de la misma solicitud: stock 24, costo promedio RD$ 983.33, solicitud en `Received` | Pasa |
| 34 | Faltante mayor que el stock: se rechaza y no cambia nada | Pasa |
| 35 | Movimiento de un producto que no existe: se rechaza | Pasa |
| 36 | Merma de 1 cebolla: stock 48 → 47 y fila `SHRINKAGE` | Pasa |
| 37 | Cancelar un pedido ya despachado: stock devuelto (`CANCEL_RETURN`), factura `Cancelled`, despacho `Cancelled`, repartidor libre y aviso pendiente de WhatsApp | Pasa |
| 38 | Registrar un pago sobre una factura cancelada: se rechaza | Pasa |
| 39 | Informe del dueño con el resumen contable: ventas 2,500, costo de ventas 1,800, margen 700, compras 20,000, ajustes −50 y por cobrar 2,500, iguales al cálculo a mano | Pasa |
| 40 | Valor del inventario del informe (RD$ 505,363.92) igual a un cálculo independiente con los datos del Sheet | Pasa |

## Problemas encontrados y corregidos

- **Chat devolvía la fila del registro**: con `lastNode` la respuesta era la de la rama del log. Se cambió el Chat Trigger a modo `streaming`.
- **Error 429 de Google Sheets**: la cuota es de 60 lecturas por minuto por usuario. Se añadieron reintentos (5 intentos, 5 s) a todos los nodos de Sheets.
- **Pedido en espera sin retomar**: no había nada que lo asignara al liberarse un repartidor. Se añadió la asignación al marcar una entrega.
- **Teléfonos como fórmula**: `+1-809-…` se interpretaba como suma. Todas las escrituras usan formato `RAW`.
- **`columns.schema` obligatorio**: los nodos de Sheets con columnas explícitas fallan sin el esquema de columnas.

## No probado

- El pago parcial (el estado `Partial`): está implementado, pero solo se probó el pago completo y el rechazo.
- La llegada de los correos a la bandeja: n8n confirmó cada envío, pero no se abrió el buzón.
- El envío real por WhatsApp: no existe todavía. Solo se comprobó que el aviso queda guardado como `whatsapp_pending`.
- El aviso "en camino" sin correo (solo se probó con correo y el de la factura sin correo).
- Cancelar un pedido ya pagado (factura `Refund pending`), cancelar un pedido que esperaba repartidor, devoluciones de cliente y ajustes por sobrante.
- Los formularios de inventario desde un navegador real: se enviaron desde un script con codificación UTF-8. El tipo de movimiento se reconoce por el texto exacto de la opción, así que un envío con la codificación dañada se rechaza con "Elige un tipo de movimiento".
- El disparo automático de las 21:00: se ejecutó el flujo a mano, no se esperó a la hora.
- La tienda en un navegador con una persona real: los clics de las capturas fueron simulados con un script, y la pantalla de confirmación se vio con una respuesta del servidor simulada. El pedido real se probó por la API.
- La tienda en pantallas de menos de 500 px de ancho (el navegador de pruebas no baja de ese ancho).
