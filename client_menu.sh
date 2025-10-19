#!/bin/bash

# Menu del Cliente PyScale VPN
SERVER_URL="https://pyscaled.canariannode.uk"

show_menu() {
    echo "=========================================="
    echo "    PyScale VPN - Menu del Cliente"
    echo "=========================================="
    echo "1. Conectar nodo a la red"
    echo "2. Ver estado del nodo"
    echo "3. Listar peers"
    echo "4. Hacer ping a un peer"
    echo "5. Enviar mensaje a un peer"
    echo "6. Monitor en tiempo real"
    echo "7. Modo interactivo"
    echo "8. Configurar servidor"
    echo "9. Salir"
    echo "=========================================="
}

connect_node() {
    echo -n "Ingresa el nombre de tu nodo: "
    read node_name
    if [ -n "$node_name" ]; then
        python -m client.cli connect --name "$node_name"
    else
        echo "Error: El nombre del nodo no puede estar vacío"
    fi
}

show_status() {
    python -m client.cli status
}

list_peers() {
    python -m client.cli peers
}

ping_peer() {
    echo "=== Lista de Peers Disponibles ==="
    python -m client.cli peers
    echo "=================================="
    echo -n "Ingresa el nombre o ID del peer: "
    read peer_id
    if [ -n "$peer_id" ]; then
        python -m client.cli ping "$peer_id"
    else
        echo "Error: El ID del peer no puede estar vacío"
    fi
}

send_message() {
    echo "=== Lista de Peers Disponibles ==="
    python -m client.cli peers
    echo "=================================="
    echo -n "Ingresa el nombre o ID del peer: "
    read peer_id
    echo -n "Ingresa el mensaje: "
    read message
    if [ -n "$peer_id" ] && [ -n "$message" ]; then
        python -m client.cli message "$peer_id" "$message"
    else
        echo "Error: Peer y mensaje no pueden estar vacíos"
    fi
}

start_monitor() {
    python -m client.cli monitor
}

start_interactive() {
    python -m client.client_admin_cli interactive
}

configure_server() {
    echo -n "Ingresa la URL del servidor (actual: $SERVER_URL): "
    read new_server
    if [ -n "$new_server" ]; then
        SERVER_URL="$new_server"
        echo "Servidor configurado a: $SERVER_URL"
        echo "Nota: Los comandos del cliente usan https://pyscaled.canariannode.uk por defecto."
        echo "Para cambiar el servidor en los comandos, necesitas modificar"
        echo "la configuración directamente en el código o usar el modo interactivo."
    else
        echo "URL del servidor no cambiada"
    fi
}

# Menu principal
while true; do
    show_menu
    echo -n "Selecciona una opción [1-9]: "
    read choice
    
    case $choice in
        1) connect_node ;;
        2) show_status ;;
        3) list_peers ;;
        4) ping_peer ;;
        5) send_message ;;
        6) start_monitor ;;
        7) start_interactive ;;
        8) configure_server ;;
        9) 
            echo "Saliendo del menu del cliente..."
            exit 0
            ;;
        *)
            echo "Opción inválida. Por favor, selecciona una opción del 1 al 9."
            ;;
    esac
    
    echo
    echo "Presiona Enter para continuar..."
    read
    clear
done
