# Estructura de la hoja de cálculo

Crea un Google Sheet con **9 pestañas**. Cada una lleva solo la fila de encabezados (fila 1), con estos nombres exactos y en este orden. Los flujos buscan las pestañas por nombre.

| Pestaña | Columnas |
|---|---|
| `Products` | SKU, Name, Category, Unit, Price, Stock, Reorder_Level, Supplier_Email |
| `Customers` | Customer_ID, Name, Phone, Email, Address, City, Created_At |
| `Orders` | Order_ID, Date, Customer_ID, Items, Subtotal, Discount, Total, Status, Payment_Status, Channel |
| `Invoices` | Invoice_No, Order_ID, Date, Amount, Due_Date, Status |
| `Payments` | Payment_ID, Invoice_No, Date, Amount, Method |
| `Purchase_Requests` | PR_ID, Date, SKU, Qty, Supplier_Email, Status |
| `Dispatch` | Dispatch_ID, Order_ID, Rider, Vehicle, Dispatched_At, Delivered_At, Status |
| `Staff` | Staff_ID, Name, Role, Phone, Vehicle, Available |
| `Activity_Log` | Time, Agent, Action, Ref_ID, Details |

## Valores que usan los flujos

- **Orders.Status**: `New` → `Invoiced` → `Dispatched` (o `Waiting for rider`) → `Delivered`
- **Orders.Payment_Status**: `Unpaid` → `Partial` → `Paid`
- **Invoices.Status**: `Unpaid` → `Partial` → `Paid`
- **Dispatch.Status**: `Dispatched` → `Delivered`
- **Staff.Available**: `Yes` / `No`
- **Purchase_Requests.Status**: `Requested`
- **Números**: `INV-1001`, `ORD-1001`, `CUS-1001`, `DSP-1001`, `PAY-1001` (cada flujo calcula el siguiente leyendo la hoja)
- **Activity_Log.Action** del agente `Notify`: `email_sent` (aviso enviado por correo) y `whatsapp_pending` (cliente sin correo; en `Details` van el evento, el teléfono y el texto listo para enviar por WhatsApp)
- **Customers.Email** puede quedar vacío: el teléfono es el dato obligatorio

Los datos de ejemplo están en `products.csv` y `staff.csv`. El flujo `Demo Traders - Seed Data` los carga por SKU y por Staff_ID, así que se puede repetir sin duplicar filas (restaura el stock inicial).
