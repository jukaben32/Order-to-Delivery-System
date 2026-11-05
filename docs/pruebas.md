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

## Problemas encontrados y corregidos

- **Chat devolvía la fila del registro**: con `lastNode` la respuesta era la de la rama del log. Se cambió el Chat Trigger a modo `streaming`.
- **Error 429 de Google Sheets**: la cuota es de 60 lecturas por minuto por usuario. Se añadieron reintentos (5 intentos, 5 s) a todos los nodos de Sheets.
- **Pedido en espera sin retomar**: no había nada que lo asignara al liberarse un repartidor. Se añadió la asignación al marcar una entrega.
- **Teléfonos como fórmula**: `+1-809-…` se interpretaba como suma. Todas las escrituras usan formato `RAW`.
- **`columns.schema` obligatorio**: los nodos de Sheets con columnas explícitas fallan sin el esquema de columnas.

## No probado

- El pago parcial (el estado `Partial`): está implementado, pero solo se probó el pago completo y el rechazo.
- La llegada de los correos a la bandeja: n8n confirmó cada envío, pero no se abrió el buzón.
- El disparo automático de las 21:00: se ejecutó el flujo a mano, no se esperó a la hora.
