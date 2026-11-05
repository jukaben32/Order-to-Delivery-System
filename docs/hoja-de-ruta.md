# Hoja de ruta

Lo que falta para llevar el concepto a producción.

## 1. Infraestructura
- Mover n8n a un **VPS** con HTTPS y dominio propio.
- Pasar la base de datos de n8n a Postgres y hacer copias de seguridad.
- Con un dominio propio se puede **publicar la app de Google** y acabar con la caducidad de los tokens cada 7 días.
- Pasar los datos de Google Sheets a una base de datos real (Postgres o Supabase) cuando el volumen supere unos pocos pedidos por minuto.

## 2. Canales
- **WhatsApp**: Evolution API para pruebas, la API oficial de Meta para producción. El flujo de negocio no cambia: solo la entrada y la salida del Front Desk.
- La tienda web puede pasar a **Vercel** como página estática, apuntando al n8n público.

## 3. Pagos
- **Stripe**: pago con tarjeta, con confirmación por webhook antes de despachar.
- **Transferencia bancaria**: referencia del pedido y confirmación manual con el formulario "Record payment".

## 4. Producto
- Fotos reales de productos (columna `Image_URL`).
- Cuentas de cliente e historial de pedidos.
- Horarios, zonas de entrega y costo de envío.
- Panel para el dueño y para los operadores de pedidos.
- Detectar pedidos facturados sin repartidor (hoy el informe nocturno no los marca).

## 5. Seguridad
- Límite de uso y verificación anti-bots en la tienda y el chat.
- Credenciales fuera del repositorio, rotación de contraseñas y registro de accesos.
