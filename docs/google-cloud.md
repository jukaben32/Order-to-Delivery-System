# Configurar Google Cloud para n8n

Los flujos usan Google Sheets y Gmail con OAuth2. Estos son los pasos que se siguieron.

## 1. Proyecto y APIs

1. En [Google Cloud Console](https://console.cloud.google.com/projectcreate) crea el proyecto `Order to Delivery System`.
2. Activa tres APIs en **APIs y servicios > Biblioteca**: *Google Sheets API*, *Google Drive API* y *Gmail API*.

## 2. Pantalla de consentimiento

1. Abre **Google Auth Platform** y pulsa **Comenzar**.
2. Nombre de la app: `Order to Delivery System`. Correo de asistencia y de contacto: el tuyo. Público: **Externo**.
3. En **Público > Usuarios de prueba**, añade todas las cuentas de Google que vas a conectar en n8n (la dueña del Sheet y la que envía los correos).

> **Modo Prueba**: mientras la app no esté publicada, Google caduca el acceso cada 7 días y hay que reconectar las credenciales en n8n. Publicar la app exige una página principal y una política de privacidad en un dominio propio. Las páginas de Google Sites no son aceptadas como dominio autorizado.

## 3. Cliente OAuth

1. En **Clientes > Crear cliente** elige **Aplicación web** y ponle un nombre (por ejemplo `n8n local`).
2. En **URI de redireccionamiento autorizados** pega la URL que muestra n8n en la credencial (en una instalación local es `http://localhost:5678/rest/oauth2-credential/callback`).
3. Al crear el cliente, **copia el Client Secret en ese momento**. Google no lo vuelve a mostrar. Si lo pierdes, borra el cliente y crea otro.

## 4. Credenciales en n8n

En n8n crea **Google Sheets OAuth2 API** y **Gmail OAuth2 API**, pega el Client ID y el Client Secret y pulsa **Sign in with Google**. Si aparece "Google no verificó esta app", entra en **Configuración avanzada** y elige **Ir a Order to Delivery System**.
