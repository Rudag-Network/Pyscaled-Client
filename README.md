# 🐍 PyScale - VPN Mesh en Python

Este proyecto implementa una VPN Mesh similar a Tailscale/Headscale, pero construida completamente en Python. Incluye un servidor de coordinación y un cliente VPN que utiliza WireGuard para establecer conexiones seguras entre nodos.

## 📖 Documentación Completa e Instrucciones de Uso

Para una guía detallada sobre la instalación, configuración y uso de PyScale, por favor consulta el archivo [instrucciones.md](instrucciones.md).

## 📋 Lista de Comandos

Para una lista completa de todos los comandos disponibles para el cliente y el CLI administrativo del servidor, consulta el archivo [listadecomandos.txt](listadecomandos.txt).

## 🚀 Características Principales

-   **Servidor de coordinación** (Headscale-like)
-   **Cliente VPN** (Tailscale-like)
-   **Encriptación end-to-end** (X25519 + ChaCha20-Poly1305)
-   **Comunicación en tiempo real** con WebSockets
-   **Configuración automática de WireGuard**
-   **NAT traversal**
-   **Mesh networking**
-   **CLI completa** para cliente y administración del servidor
-   **Monitor de red en tiempo real**
-   **Base de datos SQLite** para persistencia de datos del servidor

## ⚙️ Estructura del Proyecto

```
pyscale/
├── server/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   └── server_admin_cli.py  # Nuevo CLI administrativo del servidor
├── client/
│   ├── __init__.py
│   ├── cli.py
│   ├── crypto.py
│   └── client_admin_cli.py  # Nuevo CLI interactivo del cliente
├── scripts/
│   ├── install.sh
│   └── setup_network.sh
├── requirements.txt
├── README.md
├── instrucciones.md         # Documentación detallada del proyecto
└── listadecomandos.txt      # Lista de todos los comandos disponibles
```
