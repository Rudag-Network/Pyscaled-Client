#!/bin/bash
# Script para configurar la red y permisos

echo "🔧 Configurando red para PyScale..."

# Verificar si somos root
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  Este script necesita permisos de root. Ejecuta con sudo."
    exit 1
fi

# Habilitar IP forwarding
echo "🌐 Habilitando IP forwarding..."
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -p

# Configurar reglas iptables para NAT
echo "🔀 Configurando NAT..."
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
iptables -A FORWARD -i pyscale0 -j ACCEPT
iptables -A FORWARD -o pyscale0 -j ACCEPT

# Hacer las reglas persistentes
echo "💾 Guardando reglas iptables..."
apt-get install -y iptables-persistent
iptables-save > /etc/iptables/rules.v4

echo "✅ Configuración de red completada!"
echo ""
echo "📖 Para hacer persistente la configuración:"
echo "   - Las reglas iptables se guardaron con iptables-persistent"
echo "   - IP forwarding está habilitado en sysctl.conf"
