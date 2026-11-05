# WhatsApp con OpenWA (modo prueba)

Dos piezas:

1. **`Demo Traders - WhatsApp Gateway`** (`workflows/12-whatsapp-gateway.json`): OpenWA envía cada mensaje recibido (`message.received`) a un webhook de n8n. El flujo ignora grupos, mensajes propios, no texto y duplicados, responde solo a los números de la lista `ALLOW`, pasa el mensaje a un agente (mismas herramientas que el chat: Order agent, Support agent y Products), con memoria por teléfono, y contesta con `send-text`.
2. **`Notify Customer`**: además del correo, envía el aviso por WhatsApp si el teléfono está en la lista `ALLOW`. Si no hay correo y no se puede enviar, queda como `whatsapp_pending`.

## Seguridad
- La sesión de OpenWA es un WhatsApp real. Mientras la lista `ALLOW` esté vacía el bot no responde ni envía a nadie.
- La lista de números no se guarda en el repositorio (los archivos del repo la llevan vacía). Se define al generar: `WA_ALLOW=18095551234 python tools/build_whatsapp.py`.
- El webhook usa una ruta aleatoria y la clave de OpenWA vive solo en la credencial `OpenWA API key` de n8n.

## Registro del webhook en OpenWA
`POST /api/sessions/<id>/webhooks` con la URL del webhook de n8n y el evento `message.received`.
