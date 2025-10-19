# Instrucciones del Proyecto PyScale VPN Mesh

Este documento detalla cómo configurar, ejecutar y utilizar el proyecto PyScale VPN Mesh, que incluye un servidor de coordinación y un cliente VPN.

## 1. Configuración del Entorno

### Requisitos
- Python 3.8+
- `pip` (administrador de paquetes de Python)
- `sudo` (para la configuración de WireGuard)
- `iproute2` (generalmente preinstalado en sistemas Linux)
- `wireguard-tools` (instalar con `sudo apt install wireguard-tools` o equivalente)

### Pasos de Configuración

1.  **Clonar el Repositorio (si aún no lo has hecho):**
    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd pyscale
    ```
    (Asegúrate de reemplazar `<URL_DEL_REPOSITORIO>` con la URL real de tu repositorio.)

2.  **Crear y Activar un Entorno Virtual:**
    Es altamente recomendable usar un entorno virtual para gestionar las dependencias.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

## 2. Configuración del Servidor PyScale

El servidor PyScale utiliza un archivo de configuración y una base de datos SQLite para almacenar la información de los nodos.

### Archivo de Configuración del Servidor
El servidor generará automáticamente un archivo de configuración por defecto y una base de datos SQLite la primera vez que se ejecute.

-   **Ubicación del archivo de configuración:** `~/.pyscale/server/config.yaml` (se generará automáticamente)
-   **Ubicación de la base de datos SQLite:** `~/.pyscale/server/data/pyscale.db` (se generará automáticamente)

Puedes modificar `config.yaml` para ajustar la configuración del servidor (puertos, CIDR de la red VPN, etc.).

### Ejecutar el Servidor

Para iniciar el servidor PyScale:
```bash
source venv/bin/activate
python -m server.main
```
El servidor se ejecutará en `http://localhost:8000` por defecto.

## 3. Uso del Cliente PyScale

El cliente PyScale se conecta al servidor y configura una interfaz WireGuard para unirse a la VPN Mesh.

### Registrar un Nodo (Primera Vez)

Antes de poder usar el cliente, debes registrar tu nodo con el servidor.
```bash
source venv/bin/activate
python -m client.cli connect --name <nombre_de_tu_nodo>
```
Reemplaza `<nombre_de_tu_nodo>` con un nombre único para tu cliente (ej. `nodo-oficina`, `laptop-casa`).

Una vez registrado, el cliente guardará su configuración en `~/.pyscale/client/config.json`.

### Comandos del Cliente

El cliente PyScale ofrece varios comandos para interactuar con la red.

-   **`status`**: Muestra el estado actual del nodo, su IP, el servidor al que está conectado y una lista de peers.
    ```bash
    python -m client.cli status
    ```

-   **`peers`**: Lista todos los peers conocidos por el cliente.
    ```bash
    python -m client.cli peers
    ```

-   **`ping <peer_name_or_id>`**: Envía un ping a un peer específico por su nombre o ID.
    ```bash
    python -m client.cli ping nodo-casa
    ```

-   **`message <peer_name_or_id> <mensaje>`**: Envía un mensaje directo a un peer específico.
    ```bash
    python -m client.cli message nodo-casa "¡Hola desde PyScale!"
    ```

-   **`monitor`**: Inicia un monitor en tiempo real de la red, mostrando el estado de tu nodo y los peers.
    ```bash
    python -m client.cli monitor
    ```

### Modo Interactivo del Cliente

Para una experiencia de línea de comandos más interactiva, puedes usar el modo interactivo del cliente:
```bash
source venv/bin/activate
python -m client.client_admin_cli interactive
```
Dentro del modo interactivo, puedes escribir `help` para ver los comandos disponibles y `exit` para salir.

## 4. Uso del CLI Administrativo del Servidor

El CLI administrativo del servidor (`server_admin_cli.py`) te permite gestionar los nodos registrados y obtener información de la red directamente desde la línea de comandos, interactuando con la API del servidor.

### Comandos Administrativos

-   **`list-nodes`**: Lista todos los nodos registrados en el servidor.
    ```bash
    source venv/bin/activate
    python -m server.server_admin_cli list-nodes
    ```

-   **`get-node <node_id>`**: Obtiene información detallada de un nodo específico por su ID.
    ```bash
    source venv/bin/activate
    python -m server.server_admin_cli get-node <node_id>
    ```
    (Puedes obtener el `node_id` de la salida de `list-nodes` o `client.cli status`).

-   **`delete-node <node_id>`**: Elimina un nodo del servidor por su ID.
    ```bash
    source venv/bin/activate
    python -m server.server_admin_cli delete-node <node_id>
    ```
    **¡Cuidado!** Esta acción es irreversible.

-   **`update-node <node_id> [opciones]`**: Actualiza la información de un nodo por su ID.
    ```bash
    source venv/bin/activate
    python -m server.server_admin_cli update-node <node_id> --name nuevo-nombre --ip-address 10.100.0.X/24
    ```
    Opciones disponibles: `--name`, `--public-key`, `--ip-address`, `--endpoint`.

-   **`network-status`**: Muestra un resumen del estado general de la red PyScale.
    ```bash
    source venv/bin/activate
    python -m server.server_admin_cli network-status
    ```

## 5. Consideraciones de Seguridad

-   **`sudo`**: El cliente PyScale requiere `sudo` para configurar la interfaz WireGuard. Asegúrate de entender los riesgos asociados con la ejecución de comandos con `sudo`.
-   **Claves Privadas**: Las claves privadas de WireGuard se almacenan en `~/.pyscale/client/config.json`. Protege este archivo adecuadamente.
-   **Servidor**: Asegura tu servidor PyScale adecuadamente, especialmente si lo expones a Internet.

---
