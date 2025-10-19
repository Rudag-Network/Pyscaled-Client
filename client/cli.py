#!/usr/bin/env python3
"""
PyScale CLI - Cliente para VPN Mesh
Similar a Tailscale pero 100% Python
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

import click
import requests
import websockets
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich import box

from .crypto import PyScaleCrypto

console = Console()

class PyScaleClient:
    """Cliente principal de PyScale"""
    
    def __init__(self, server_url: str, interface: str = "pyscale0", private_key_b64: Optional[str] = None):
        self.server_url = server_url.rstrip('/')
        self.interface = interface
        self.crypto = PyScaleCrypto(private_key_b64=private_key_b64)
        self.node_id: Optional[str] = None
        self.node_name: Optional[str] = None
        self.ip_address: Optional[str] = None
        self.network_cidr: Optional[str] = None
        self.peers: Dict[str, dict] = {}
        self.shared_keys: Dict[str, bytes] = {}  # node_id -> shared_key
        self.running = False
        self.websocket = None
        self.config_dir = Path.home() / '.pyscale' / 'client'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuración de WireGuard
        self.wg_config = {
            "private_key": self.crypto.get_private_key_b64(),
            "listen_port": 51820
        }
    
    async def register(self, name: str) -> bool:
        """Registrar este nodo con el servidor"""
        try:
            public_key_b64 = self.crypto.get_public_key_b64()
            
            response = requests.post(
                f"{self.server_url}/api/v1/node/register",
                json={
                    "name": name,
                    "public_key": public_key_b64,
                    "endpoint": self._get_public_endpoint()
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.node_id = data["node_id"]
                self.node_name = name
                self.ip_address = data.get("ip_address", "")
                self.network_cidr = data.get("network_cidr", None)
                
                # Guardar configuración
                self._save_config()
                
                console.print(f"✅ [green]Registrado como[/green] [bold]{name}[/bold] ([cyan]{self.node_id}[/cyan])")
                if self.ip_address:
                    console.print(f"📡 [blue]IP asignada:[/blue] {self.ip_address}")
                return True
            else:
                console.print(f"❌ [red]Error en registro:[/red] {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            console.print(f"❌ [red]Error de conexión al servidor:[/red] {str(e)}")
            return False
    
    def _get_public_endpoint(self) -> str:
        """Obtener endpoint público (simplificado)"""
        # En una implementación real, aquí detectaríamos la IP pública
        # Por ahora, usamos un placeholder
        return "dynamic"
    
    def _save_config(self):
        """Guardar configuración del cliente"""
        config = {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "server_url": self.server_url,
            "public_key": self.crypto.get_public_key_b64(),
            "private_key": self.crypto.get_private_key_b64(),
            "ip_address": self.ip_address,
            "interface": self.interface,
            "network_cidr": self.network_cidr
        }
        
        config_file = self.config_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _load_config(self) -> bool:
        """Cargar configuración existente"""
        config_file = self.config_dir / "config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                self.node_id = config["node_id"]
                self.node_name = config["node_name"]
                self.server_url = config["server_url"]
                self.ip_address = config.get("ip_address")
                self.network_cidr = config.get("network_cidr")
                self.crypto = PyScaleCrypto(private_key_b64=config["private_key"])
                self.wg_config["private_key"] = config["private_key"]
                
                return True
            except Exception as e:
                console.print(f"❌ [red]Error cargando configuración:[/red] {str(e)}")
        
        return False
    
    def setup_wireguard_interface(self):
        """Configurar interfaz de WireGuard"""
        try:
            console.print("🔧 [yellow]Configurando interfaz WireGuard...[/yellow]")
            
            # Verificar si la interfaz ya existe
            result = subprocess.run(
                ['ip', 'link', 'show', self.interface],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # Crear interfaz WireGuard
                subprocess.run([
                    "sudo", "ip", "link", "add", "dev", self.interface, "type", "wireguard"
                ], check=True, capture_output=True)
                console.print(f"✅ [green]Interfaz {self.interface} creada[/green]")
            
            # Configurar IP si está asignada
            if self.ip_address:
                # Check if IP is already assigned
                ip_check_result = subprocess.run(
                    ['ip', 'addr', 'show', 'dev', self.interface],
                    capture_output=True,
                    text=True
                )
                if self.ip_address.split('/')[0] not in ip_check_result.stdout:
                    subprocess.run([
                        "sudo", "ip", "addr", "add", self.ip_address, "dev", self.interface
                    ], check=True, capture_output=True)
                else:
                    console.print(f"ℹ️ [yellow]IP {self.ip_address} ya asignada a {self.interface}[/yellow]")
            
            # Configurar clave privada en WireGuard
            process = subprocess.run([
                "sudo", "wg", "set", self.interface, 
                "private-key", "/dev/stdin"
            ], input=self.wg_config["private_key"].encode(), capture_output=True)
            
            if process.returncode != 0:
                console.print(f"❌ [red]Error configurando WireGuard:[/red] {process.stderr.decode()}")
                return False
            
            # Configurar puerto de escucha
            subprocess.run([
                "sudo", "wg", "set", self.interface,
                "listen-port", str(self.wg_config["listen_port"])
            ], check=True, capture_output=True)
            
            # Activar interfaz
            subprocess.run([
                "sudo", "ip", "link", "set", "up", "dev", self.interface
            ], check=True, capture_output=True)
            
            # Add route for the VPN network
            if self.network_cidr:
                subprocess.run([
                    "sudo", "ip", "route", "add", self.network_cidr, "dev", self.interface
                ], check=True, capture_output=True)
            
            console.print(f"✅ [green]Interfaz WireGuard {self.interface} configurada y activada[/green]")
            return True
            
        except subprocess.CalledProcessError as e:
            console.print(f"❌ [red]Error configurando WireGuard:[/red] {str(e)}")
            return False
    
    def update_wireguard_peers(self):
        """Actualizar peers en WireGuard"""
        if not self.peers:
            console.print("ℹ️ [yellow]No hay peers para configurar[/yellow]")
            return
        
        for peer_id, peer_info in self.peers.items():
            try:
                if not peer_info.get('public_key') or not peer_info.get('endpoint'):
                    continue
                
                # Construir comando WireGuard
                cmd = [
                    "sudo", "wg", "set", self.interface,
                    "peer", peer_info["public_key"],
                    "allowed-ips", peer_info.get("ip_address", "0.0.0.0/0").split('/')[0] + "/32"
                ]
                
                # Agregar endpoint si está disponible
                if peer_info.get('endpoint') and peer_info['endpoint'] != 'dynamic':
                    cmd.extend(["endpoint", peer_info['endpoint']])
                
                # Agregar puerto si está en el endpoint
                if ':' in peer_info.get('endpoint', ''):
                    cmd.extend(["endpoint", peer_info['endpoint']])
                
                subprocess.run(cmd, check=True, capture_output=True)
                console.print(f"✅ [green]Peer añadido:[/green] {peer_info['name']}")
                
            except subprocess.CalledProcessError as e:
                console.print(f"❌ [red]Error añadiendo peer {peer_info['name']}:[/red] {str(e)}")
    
    async def fetch_peers(self):
        """Obtener lista de peers del servidor"""
        if not self.node_id:
            console.print("❌ [red]No hay node_id, registrarse primero[/red]")
            return
        
        try:
            response = requests.get(
                f"{self.server_url}/api/v1/node/{self.node_id}/peers",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                old_count = len(self.peers)
                self.peers = {
                    peer["node_id"]: peer for peer in data["peers"]
                }
                
                new_count = len(self.peers)
                if new_count > old_count:
                    console.print(f"🔄 [blue]Lista de peers actualizada:[/blue] {new_count} peers")
                    self.update_wireguard_peers()
                
                return True
            else:
                console.print(f"❌ [red]Error obteniendo peers:[/red] {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            console.print(f"❌ [red]Error de conexión:[/red] {str(e)}")
            return False
    
    async def websocket_handler(self):
        """Manejar conexión WebSocket con el servidor"""
        while self.running:
            try:
                async with websockets.connect(
                    f"ws://{self.server_url.replace('http://', '').replace('https://', '')}/ws/{self.node_id}"
                ) as websocket:
                    
                    self.websocket = websocket
                    console.print("🔗 [green]Conectado al servidor vía WebSocket[/green]")
                    
                    # Heartbeat en segundo plano
                    async def send_heartbeat():
                        while self.running and self.websocket:
                            try:
                                await websocket.send(json.dumps({
                                    "type": "heartbeat",
                                    "timestamp": datetime.now().isoformat()
                                }))
                                await asyncio.sleep(30)  # Cada 30 segundos
                            except Exception:
                                break
                    
                    heartbeat_task = asyncio.create_task(send_heartbeat())
                    
                    # Escuchar mensajes
                    try:
                        async for message in websocket:
                            await self.handle_server_message(json.loads(message))
                    except websockets.exceptions.ConnectionClosed:
                        console.print("🔌 [yellow]Conexión WebSocket cerrada[/yellow]")
                    finally:
                        heartbeat_task.cancel()
                        self.websocket = None
                    
            except Exception as e:
                console.print(f"❌ [red]Error WebSocket:[/red] {str(e)}, reconectando en 5s...")
                await asyncio.sleep(5)
    
    async def handle_server_message(self, message: dict):
        """Manejar mensajes del servidor"""
        msg_type = message.get("type")
        
        if msg_type == "welcome":
            console.print(f"👋 [green]{message.get('message', 'Connected')}[/green]")
        
        elif msg_type == "peer_list":
            old_peers = set(self.peers.keys())
            new_peers = {peer["node_id"]: peer for peer in message.get("peers", [])}
            
            # Detectar cambios
            added_peers = set(new_peers.keys()) - old_peers
            removed_peers = old_peers - set(new_peers.keys())
            
            self.peers = new_peers
            
            if added_peers or removed_peers:
                console.print("🔄 [blue]Lista de peers actualizada[/blue]")
                self.update_wireguard_peers()
        
        elif msg_type == "peer_status_changed":
            node_id = message.get("node_id")
            is_online = message.get("is_online")
            
            if node_id in self.peers:
                status_text = "🟢 EN LÍNEA" if is_online else "🔴 OFFLINE"
                console.print(f"📡 [yellow]Peer {self.peers[node_id]['name']} está ahora {status_text}[/yellow]")
        
        elif msg_type == "direct_message":
            from_node = message.get("from_node")
            content = message.get("content")
            
            peer_name = "Unknown"
            if from_node in self.peers:
                peer_name = self.peers[from_node]["name"]
            
            console.print(f"✉️ [blue]Mensaje de {peer_name}:[/blue] {content}")
    
    async def start(self) -> bool:
        """Iniciar el cliente"""
        self.running = True
        
        if not self.node_id or not self.node_name:
            console.print("❌ [red]El cliente no está inicializado correctamente. Registre o cargue la configuración primero.[/red]")
            return False
        
        console.print(f"🚀 [green]Iniciando PyScale Client[/green]")
        console.print(f"   📝 Nombre: [bold]{self.node_name}[/bold]")
        console.print(f"   🆔 ID: [cyan]{self.node_id}[/cyan]")
        console.print(f"   🌐 Servidor: [blue]{self.server_url}[/blue]")
        
        # Configurar WireGuard
        if not self.setup_wireguard_interface():
            return False
        
        # Obtener peers iniciales
        await self.fetch_peers()
        
        # Iniciar WebSocket en segundo plano
        asyncio.create_task(self.websocket_handler())
        
        console.print("✅ [green]PyScale Client iniciado correctamente[/green]")
        return True
    
    async def stop(self):
        """Detener el cliente"""
        self.running = False
        
        if self.websocket:
            await self.websocket.close()
        
        # Limpiar interfaz WireGuard
        try:
            subprocess.run([
                "sudo", "ip", "link", "delete", "dev", self.interface
            ], check=True, capture_output=True)
            console.print(f"✅ [green]Interfaz {self.interface} eliminada[/green]")
        except subprocess.CalledProcessError:
            pass
        
        console.print("🛑 [yellow]PyScale Client detenido[/yellow]")
    
    async def send_message(self, target: str, message: str):
        """Enviar mensaje a un peer"""
        # Buscar peer por nombre o ID
        target_peer = None
        for peer_id, peer_info in self.peers.items():
            if peer_info['name'] == target or peer_id == target:
                target_peer = peer_info
                target_peer['id'] = peer_id
                break
        
        if not target_peer:
            console.print(f"❌ [red]Peer '{target}' no encontrado[/red]")
            return False
        
        if not self.websocket:
            console.print("❌ [red]No hay conexión WebSocket activa[/red]")
            return False
        
        try:
            # Derivar clave compartida si no existe
            if target_peer['id'] not in self.shared_keys:
                shared_key = self.crypto.derive_shared_key(target_peer['public_key'])
                self.shared_keys[target_peer['id']] = shared_key
            
            # Encriptar mensaje
            encrypted_msg = self.crypto.encrypt_message(message, self.shared_keys[target_peer['id']])
            
            await self.websocket.send(json.dumps({
                "type": "direct_message",
                "target_node": target_peer['id'],
                "content": message,
                "encrypted_message": encrypted_msg
            }))
            
            console.print(f"✅ [green]Mensaje enviado a {target_peer['name']}[/green]")
            return True
            
        except Exception as e:
            console.print(f"❌ [red]Error enviando mensaje:[/red] {str(e)}")
            return False
    
    async def ping_peer(self, target: str):
        """Hacer ping a un peer"""
        target_peer = None
        for peer_id, peer_info in self.peers.items():
            if peer_info['name'] == target or peer_id == target:
                target_peer = peer_info
                break
        
        if not target_peer or not target_peer.get('ip_address'):
            console.print(f"❌ [red]Peer '{target}' no encontrado o sin IP[/red]")
            return
        
        ip = target_peer['ip_address'].split('/')[0]
        console.print(f"[DEBUG] IP extracted for ping: {ip}")
        
        console.print(f"🏓 [yellow]Haciendo ping a {target_peer['name']} ({ip})...[/yellow]")
        
        try:
            result = subprocess.run(
                ['ping', '-c', '4', ip],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                console.print(Panel(result.stdout, title=f"✅ Ping exitoso a {target}", border_style="green"))
            else:
                console.print(Panel(result.stderr, title=f"❌ Ping fallido a {target}", border_style="red"))
                
        except subprocess.TimeoutExpired:
            console.print(f"❌ [red]Timeout haciendo ping a {target}[/red]")
        except Exception as e:
            console.print(f"❌ [red]Error haciendo ping:[/red] {str(e)}")

# Comandos CLI con Click
@click.group()
@click.option('--server', default='https://pyscaled.canariannode.uk', help='URL del servidor PyScale') 
@click.pass_context
def cli(ctx, server):
    """PyScale CLI - VPN Mesh en Python"""
    ctx.ensure_object(dict)
    ctx.obj['client'] = PyScaleClient(server)

@cli.command()
@click.option('--name', required=True, help='Nombre para este nodo')
@click.pass_context
def connect(ctx, name):
    """Conectar a la red PyScale"""
    client = ctx.obj['client']
    
    async def _connect():
        # Always try to load existing config first to get node_id if available
        client._load_config() # No need to check return, register will handle it

        if not await client.register(name):
            return # Registration failed

        # If registration was successful (or updated), then start the client
        if await client.start():
            try:
                while client.running:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                await client.stop()
    
    asyncio.run(_connect())

@cli.command()
@click.pass_context
def status(ctx):
    """Mostrar estado de la red"""
    client = ctx.obj['client']
    
    async def _status():
        if not client._load_config():
            console.print("❌ [red]No hay configuración. Usa 'connect' primero.[/red]")
            return
        
        if await client.start():
            # Cargar peers
            await client.fetch_peers()
            
            # Crear tabla de estado
            table = Table(title="🌐 Estado de PyScale", box=box.ROUNDED)
            table.add_column("Propiedad", style="cyan")
            table.add_column("Valor", style="white")
            
            table.add_row("Nodo", f"{client.node_name} ({client.node_id})")
            table.add_row("IP", client.ip_address or "No asignada")
            table.add_row("Servidor", client.server_url)
            table.add_row("Interfaz", client.interface)
            table.add_row("Peers", str(len(client.peers)))
            
            console.print(table)
            
            # Tabla de peers
            if client.peers:
                peers_table = Table(title="📋 Peers Conectados", box=box.ROUNDED)
                peers_table.add_column("Nombre", style="green")
                peers_table.add_column("ID", style="cyan")
                peers_table.add_column("IP", style="blue")
                peers_table.add_column("Estado", style="yellow")
                peers_table.add_column("Última vez", style="white")
                
                for peer in client.peers.values():
                    status = "🟢 En línea" if peer.get('is_online') else "🔴 Offline"
                    last_seen = peer.get('last_seen', 'Desconocido')
                    peers_table.add_row(
                        peer['name'],
                        peer['node_id'][:8] + "...",
                        peer.get('ip_address', 'N/A'),
                        status,
                        last_seen
                    )
                
                console.print(peers_table)
            
            await client.stop()
    
    asyncio.run(_status())

@cli.command()
@click.argument('peer')
@click.pass_context
def ping(ctx, peer):
    """Hacer ping a un peer"""
    client = ctx.obj['client']
    
    async def _ping():
        if not client._load_config():
            console.print("❌ [red]No hay configuración. Usa 'connect' primero.[/red]")
            return
        
        if await client.start():
            await asyncio.sleep(2)  # Esperar conexión
            await client.ping_peer(peer)
            await client.stop()
    
    asyncio.run(_ping())

@cli.command()
@click.argument('peer')
@click.argument('message')
@click.pass_context
def message(ctx, peer, message):
    """Enviar mensaje a un peer"""
    client = ctx.obj['client']
    
    async def _message():
        if not client._load_config():
            console.print("❌ [red]No hay configuración. Usa 'connect' primero.[/red]")
            return
        
        if await client.start():
            await asyncio.sleep(2)
            await client.send_message(peer, message)
            await asyncio.sleep(1)
            await client.stop()
    
    asyncio.run(_message())

@cli.command()
@click.pass_context
def peers(ctx):
    """Listar todos los peers"""
    client = ctx.obj['client']
    
    async def _peers():
        if not client._load_config():
            console.print("❌ [red]No hay configuración. Usa 'connect' primero.[/red]")
            return
        
        if await client.start():
            await asyncio.sleep(2)
            
            if not client.peers:
                console.print("ℹ️ [yellow]No hay peers conectados[/yellow]")
            else:
                table = Table(title="📋 Lista de Peers", box=box.ROUNDED)
                table.add_column("Nombre", style="green")
                table.add_column("ID", style="cyan")
                table.add_column("IP", style="blue")
                table.add_column("Endpoint", style="magenta")
                table.add_column("Estado", style="yellow")
                
                for peer in client.peers.values():
                    status = "🟢 En línea" if peer.get('is_online') else "🔴 Offline"
                    table.add_row(
                        peer['name'],
                        peer['node_id'][:8] + "...",
                        peer.get('ip_address', 'N/A'),
                        peer.get('endpoint', 'N/A'),
                        status
                    )
                
                console.print(table)
            
            await client.stop()
    
    asyncio.run(_peers())

@cli.command()
@click.pass_context
def monitor(ctx):
    """Monitor en tiempo real de la red"""
    client = ctx.obj['client']
    
    async def _monitor():
        if not client._load_config():
            console.print("❌ [red]No hay configuración. Usa 'connect' primero.[/red]")
            return
        
        if await client.start():
            try:
                with Live(refresh_per_second=4) as live:
                    while client.running:
                        # Actualizar datos
                        await client.fetch_peers()
                        
                        # Construir display
                        display = []
                        
                        # Información del nodo
                        display.append(
                            Panel(
                                f"[bold green]{client.node_name}[/bold green] ([cyan]{client.node_id}[/cyan])\n"
                                f"IP: [blue]{client.ip_address}[/blue]\n"
                                f"Servidor: [yellow]{client.server_url}[/yellow]\n"
                                f"Peers activos: [magenta]{len([p for p in client.peers.values() if p.get('is_online')])}[/magenta]",
                                title="🖥️ Mi Nodo",
                                border_style="green"
                            )
                        )
                        
                        # Lista de peers
                        if client.peers:
                            peers_text = ""
                            for peer in client.peers.values():
                                status_icon = "🟢" if peer.get('is_online') else "🔴"
                                peers_text += f"{status_icon} [bold]{peer['name']:15}[/bold] {peer.get('ip_address', 'N/A'):15} {peer.get('endpoint', 'N/A')}\n"
                            
                            display.append(
                                Panel(
                                    peers_text,
                                    title=f"📡 Peers ({len(client.peers)})",
                                    border_style="blue"
                                )
                            )
                        
                        live.update(Panel(
                            "\n".join(str(p) for p in display),
                            title="🌐 PyScale Monitor",
                            border_style="yellow"
                        ))
                        
                        await asyncio.sleep(5)
                        
            except KeyboardInterrupt:
                await client.stop()
    
    asyncio.run(_monitor())

if __name__ == "__main__":
    cli()
