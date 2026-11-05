# Order to Delivery System

Sistema de pedido a entrega para un colmado dominicano ("Demo Traders"), construido con **n8n**, **Google Sheets**, **Gmail** y **Claude**. El cliente hace su pedido por chat y el sistema lo factura, descuenta el inventario, asigna un repartidor y avisa por correo. Cada noche el dueño recibe un informe.

La regla de diseño más importante: **el dinero no lo calcula la IA**. La IA solo entiende palabras. Un nodo Code toma los precios de la hoja `Products` y calcula los totales, así el mismo pedido da siempre el mismo total.

## Cómo funciona

```mermaid
flowchart LR
    C[Cliente en el chat] --> FD[Front Desk Agent]
    FD -->|pedido nuevo| OA[Order Agent]
    FD -->|estado de pedido| SA[Support Agent]
    FD -->|pregunta de producto| P[(Products)]
    OA --> INV[Inventory]
    OA --> BIL[Billing]
    OA --> DSP[Dispatch]
    INV -->|stock bajo| PR[(Purchase_Requests + correo al proveedor)]
    BIL --> F[(Invoices + correo al cliente)]
    DSP --> R[(Dispatch + rider ocupado + correo)]
    MG[Manager Agent 21:00] --> O[Informe al dueño]
```

## Los 7 flujos

| # | Flujo | IA | Qué hace |
|---|---|---|---|
| 1 | **Front Desk Agent** | Sí | Chat público con memoria de 10 mensajes. Reparte cada consulta y nunca inventa un precio. |
| 2 | **Order Agent** | Sí | Extrae artículos y datos del cliente con un Structured Output Parser. Un nodo Code calcula el total. Guarda `Customers` y `Orders` y llama a Inventory, Billing y Dispatch. |
| 3 | **Support Agent** | Sí | Responde "¿dónde está ORD-xxxx?" con herramientas de solo lectura sobre `Orders` y `Dispatch`. |
| 4 | **Manager Agent** | Sí | Informe a las 21:00 y formulario "Send report now". Un Code calcula ventas, stock bajo, facturas sin pagar y entregas tardías; la IA solo redacta el correo. |
| 5 | **Inventory** | No | Resta stock con Update Row por SKU. Si baja del mínimo, crea una fila en `Purchase_Requests` (4 × `Reorder_Level`) y escribe al proveedor. |
| 6 | **Billing** | No | Siguiente factura (`INV-1001`…), vencimiento a 7 días, correo al cliente. Incluye el formulario "Record payment". |
| 7 | **Dispatch** | No | Primer repartidor con `Available = Yes`. Si no hay ninguno, el pedido espera y queda en el registro. Incluye el formulario "Mark delivered", que libera al repartidor y asigna el pedido en espera más antiguo. |

Y tres flujos de apoyo:

| Flujo | IA | Qué hace |
|---|---|---|
| **Create Order** | No | Núcleo compartido de pedidos: valida los datos, calcula los precios en código, guarda cliente y pedido y llama a Inventory, Billing y Dispatch. Lo usa la tienda web. |
| **Storefront** | No | Sirve la tienda web en `/webhook/tienda` y su API (`productos` y `pedido`). Detalles en [docs/tienda.md](docs/tienda.md). |
| **Seed Data** | No | Carga 50 productos típicos de colmado y 3 repartidores. Se puede repetir sin duplicar filas. |

Todos los flujos escriben en `Activity_Log`.

## Estructura del repositorio

```
workflows/   Exportación JSON de los 10 flujos de n8n
storefront/  Tienda web (index.html) y el script que la empaqueta en n8n
data/        Productos y repartidores de ejemplo, y estructura de la hoja
docs/        Instalación, Google Cloud, tienda web, hoja de ruta y pruebas
```

## Tienda web

Con n8n encendido, la tienda está en `http://localhost:5678/webhook/tienda`: catálogo con 50 productos por categorías, buscador, carrito editable, datos de entrega, forma de pago y pantalla de confirmación. El navegador solo envía códigos y cantidades; **el total lo calcula el servidor**. Más detalles en [docs/tienda.md](docs/tienda.md).

## Puesta en marcha

1. **Hoja de cálculo**: crea un Google Sheet con las 9 pestañas de [data/sheet-headers.md](data/sheet-headers.md).
2. **Google Cloud**: crea las credenciales OAuth siguiendo [docs/google-cloud.md](docs/google-cloud.md).
3. **n8n**: crea estas credenciales:
   - Google Sheets OAuth2 y Gmail OAuth2.
   - Anthropic (tu API key).
   - Basic Auth para los formularios del personal.
4. **Importa** los JSON de `workflows/` en este orden: Inventory, Billing, Dispatch, Create Order, Storefront, Support Agent, Order Agent, Front Desk Agent, Manager Agent, Seed Data.
5. **Reconecta las referencias** (los IDs cambian al importar):
   - En cada nodo de Google Sheets: elige tu hoja y tus credenciales.
   - En Order Agent y en Create Order: los nodos `Call Inventory`, `Call Billing` y `Call Dispatch`.
   - En Storefront: el nodo `Run Create Order`.
   - En Front Desk Agent: las herramientas `Order agent` y `Support agent`.
   - En Dispatch: el nodo `Assign waiting order`, que se llama a sí mismo.
6. **Correos de ejemplo**: cambia `proveedor@example.com` y el correo del dueño en el nodo `Compute report numbers` del Manager Agent.
7. **Zona horaria**: los flujos usan `America/Santo_Domingo`. Cámbiala en los ajustes de cada flujo si hace falta.
8. Ejecuta **Seed Data** una vez y **publica** los flujos.

## Formularios del personal

Los tres formularios están protegidos con Basic Auth y son locales a tu instancia de n8n:

| Formulario | Ruta | Quién lo usa |
|---|---|---|
| Record payment | `/form/demo-traders-record-payment` | Caja |
| Mark delivered | `/form/demo-traders-mark-delivered` | Repartidores |
| Send report now | `/form/demo-traders-send-report` | Dueño |

Para usarlos desde el móvil, n8n debe ser accesible desde internet (túnel o servidor).

## Limitaciones conocidas

- **Cuota de Google Sheets**: 60 lecturas por minuto. Un pedido gasta unas 25, por eso los nodos de Sheets tienen reintentos. Para más volumen, pasa los datos a una base de datos real.
- **Pedidos simultáneos**: dos pedidos en el mismo segundo pueden chocar en el número, porque Sheets no tiene transacciones.
- **Google en modo Prueba**: los tokens caducan cada 7 días. Para publicar la app Google exige un dominio propio con página principal y política de privacidad.
- **WhatsApp**: el chat es el hosted chat de n8n. El siguiente paso es conectarlo a WhatsApp (Evolution API, o la API oficial de Meta para producción).
- **Cadena sin transacciones**: si un paso falla a mitad de un pedido (por ejemplo, Dispatch), el pedido queda facturado sin repartidor. El informe del dueño no lo marca todavía.

## Seguridad

Este repositorio **no contiene** contraseñas, API keys ni secretos de OAuth. Los flujos solo guardan referencias a credenciales de n8n por nombre. Los correos reales se sustituyeron por `@example.com`.
