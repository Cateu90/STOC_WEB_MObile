#!/usr/bin/env python3
"""
Teste da detecção automática de IP
"""

import sys
import os

# Adiciona o diretório pai ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from util.network_info import get_ip_and_port, get_network_ip

def testar_deteccao_ip():
    print("🔍 Testando detecção automática de IP...")
    print("=" * 40)
    
    # Testa só o IP
    ip = get_network_ip()
    print(f"📍 IP detectado: {ip}")
    
    # Testa IP e porta
    ip_completo, porta = get_ip_and_port()
    print(f"🌐 IP completo: {ip_completo}")
    print(f"🔌 Porta: {porta}")
    
    print("=" * 40)
    print("✅ URL para o app Flutter:")
    print(f"   http://{ip_completo}:{porta}/api")
    print("=" * 40)
    
    # Verifica se é um IP válido de rede local
    if ip_completo.startswith(('192.168.', '10.', '172.')):
        print("✅ IP de rede local detectado corretamente!")
    elif ip_completo == '127.0.0.1':
        print("⚠️  Usando localhost - verifique sua conexão de rede")
    else:
        print(f"ℹ️  IP público ou não convencional: {ip_completo}")

if __name__ == "__main__":
    testar_deteccao_ip()
