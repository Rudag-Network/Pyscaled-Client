#!/usr/bin/env python3
"""
PyScale Client Admin CLI - Cliente interactivo para PyScale
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
from .cli import PyScaleClient # Import PyScaleClient from original cli.py

console = Console()

@click.group()
@click.option('--server', default='https://pyscaled.canariannode.uk', help='URL del servidor PyScale') #################
@click.pass_context
def cli(ctx, server):
    """PyScale Client Admin CLI - Herramienta interactiva para el cliente PyScale"""
    ctx.ensure_object(dict)
    ctx.obj['client'] = PyScaleClient(server)

@cli.command()
@click.pass_context
def interactive(ctx):
    """Iniciar el modo interactivo del cliente"""
    client = ctx.obj['client']

    async def _interactive():
        if not client._load_config():
            console.print("❌ [red]No hay configuración. Usa 'connect' primero.[/red]")
            return

        if not await client.start():
            return

        console.print(Panel("[bold green]PyScale Client - Modo Interactivo[/bold green]", expand=False))
        console.print("Escribe 'help' para ver los comandos disponibles o 'exit' para salir.")

        while client.running:
            try:
                command_line = console.input("[bold cyan]PyScale > [/bold cyan]").strip()
                if not command_line:
                    continue

                if command_line.lower() == "exit":
                    client.running = False
                    break
                elif command_line.lower() == "help":
                    console.print("""
Comandos disponibles:
  status                                 - Muestra el estado actual del nodo.
  peers                                  - Lista todos los peers conocidos.
  ping <peer_name_or_id>                 - Envía un ping a un peer específico.
  message <peer_name_or_id> <mensaje>    - Envía un mensaje a un peer específico.
  monitor                                - Inicia un monitor en tiempo real de la red.
  exit                                   - Sale del modo interactivo.
  help                                   - Muestra esta ayuda.
""")
                else:
                    # Parse command and arguments
                    parts = command_line.split(maxsplit=2)
                    cmd = parts[0]
                    args = parts[1:] if len(parts) > 1 else []

                    if cmd == "status":
                        await _status_command(client)
                    elif cmd == "peers":
                        await _peers_command(client)
                    elif cmd == "ping":
                        if len(args) == 1:
                            await client.ping_peer(args[0])
                        else:
                            console.print("❌ [red]Uso: ping <peer_name_or_id>[/red]")
                    elif cmd == "message":
                        if len(args) == 2:
                            await client.send_message(args[0], args[1])
                        else:
                            console.print("❌ [red]Uso: message <peer_name_or_id> <mensaje>[/red]")
                    elif cmd == "monitor":
                        await _monitor_command(client)
                    else:
                        console.print(f"❌ [red]Comando desconocido: {cmd}[/red]")

            except KeyboardInterrupt:
                client.running = False
                break
            except Exception as e:
                console.print(f"❌ [red]Error en modo interactivo: {e}[/red]")
        
        await client.stop()

    asyncio.run(_interactive())

async def _status_command(client: PyScaleClient):
    # Reimplementación de la lógica de status para el modo interactivo
    await client.fetch_peers()
    table = Table(title="🌐 Estado de PyScale", box=box.ROUNDED)
    table.add_column("Propiedad", style="cyan")
    table.add_column("Valor", style="white")
    table.add_row("Nodo", f"{client.node_name} ({client.node_id})")
    table.add_row("IP", client.ip_address or "No asignada")
    table.add_row("Servidor", client.server_url)
    table.add_row("Interfaz", client.interface)
    table.add_row("Peers", str(len(client.peers)))
    console.print(table)

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

async def _peers_command(client: PyScaleClient):
    # Reimplementación de la lógica de peers para el modo interactivo
    await client.fetch_peers()
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

async def _monitor_command(client: PyScaleClient):
    # Reimplementación de la lógica de monitor para el modo interactivo
    console.print("[bold yellow]Iniciando monitor... Presiona Ctrl+C para salir.[/bold yellow]")
    try:
        with Live(refresh_per_second=4) as live:
            while client.running:
                await client.fetch_peers()
                display = []
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
        console.print("[bold yellow]Monitor detenido.[/bold yellow]")
    except Exception as e:
        console.print(f"❌ [red]Error en monitor: {e}[/red]")

if __name__ == "__main__":
    cli()
