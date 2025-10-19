#!/bin/bash
# scripts/install.sh

echo "🐍 Instalando PyScale - VPN Mesh en Python..."

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no está instalado. Instalando..."
    sudo apt update
    sudo apt install -y python3 python3-pip
fi

# Instalar dependencias del sistema
echo "🔧 Instalando dependencias del sistema..."
sudo apt update
sudo apt install -y wireguard-tools iptables iproute2 net-tools

# Crear entorno virtual
echo "📁 Creando entorno virtual..."
python3 -m venv pyscale-env
source pyscale-env/bin/activate

# Instalar dependencias Python
echo "📦 Instalando dependencias Python..."
pip install -r requirements.txt

# Crear directorios de configuración
echo "📂 Creando directorios de configuración..."
mkdir -p ~/.pyscale/{server,client,logs}

# Dar permisos de ejecución
chmod +x scripts/setup_network.sh

echo "✅ Instalación completada!"
echo ""
echo "📖 Para usar PyScale:"
echo "   1. Servidor: python server/main.py"
echo "   2. Cliente: python client/cli.py --help"
echo ""
echo "🔧 Recuerda ejecutar: source pyscale-env/bin/activate"
