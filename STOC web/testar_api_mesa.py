#!/usr/bin/env python3
"""
Script para testar as APIs de mesa
"""

import requests
import json
from util.network_info import get_ip_and_port

def testar_apis_mesa():
    """Testa as APIs de mesa"""
    ip, port = get_ip_and_port()
    base_url = f"http://{ip}:{port}/api"
    
    print("🧪 Testando APIs de Mesa")
    print("=" * 50)
    
    # Dados de login
    login_data = {
        "email": "cordeiro14@outlook.com",
        "password": "123456"
    }
    
    # 1. Fazer login
    print("1. Fazendo login...")
    try:
        response = requests.post(f"{base_url}/login", json=login_data)
        if response.status_code == 200:
            login_result = response.json()
            token = login_result.get('token')
            print(f"✅ Login bem-sucedido! Token: {token[:20]}...")
        else:
            print(f"❌ Erro no login: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"❌ Erro na requisição de login: {e}")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Listar mesas existentes
    print("\n2. Listando mesas existentes...")
    try:
        response = requests.get(f"{base_url}/mesas", headers=headers)
        if response.status_code == 200:
            mesas = response.json()
            print(f"✅ Mesas encontradas: {len(mesas)}")
            for mesa in mesas:
                print(f"   - ID: {mesa['id']}, Nome: {mesa['nome']}")
        else:
            print(f"❌ Erro ao listar mesas: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
    
    # 3. Cadastrar nova mesa
    print("\n3. Cadastrando nova mesa...")
    nova_mesa_data = {"nome": "Mesa Teste API"}
    
    try:
        response = requests.post(f"{base_url}/mesas", headers=headers, data=nova_mesa_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Mesa cadastrada: {result['message']}")
            nova_mesa_id = result['mesa']['id']
        else:
            print(f"❌ Erro ao cadastrar mesa: {response.status_code} - {response.text}")
            nova_mesa_id = None
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        nova_mesa_id = None
    
    # 4. Tentar cadastrar mesa com mesmo nome (deve dar erro)
    print("\n4. Tentando cadastrar mesa com nome duplicado...")
    try:
        response = requests.post(f"{base_url}/mesas", headers=headers, data=nova_mesa_data)
        if response.status_code == 400:
            result = response.json()
            print(f"✅ Erro esperado detectado: {result['error']}")
        else:
            print(f"⚠️  Resposta inesperada: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
    
    # 5. Listar mesas novamente
    print("\n5. Listando mesas após cadastro...")
    try:
        response = requests.get(f"{base_url}/mesas", headers=headers)
        if response.status_code == 200:
            mesas = response.json()
            print(f"✅ Mesas atuais: {len(mesas)}")
            for mesa in mesas:
                print(f"   - ID: {mesa['id']}, Nome: {mesa['nome']}")
        else:
            print(f"❌ Erro ao listar mesas: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
    
    # 6. Excluir a mesa criada (se foi criada)
    if nova_mesa_id:
        print(f"\n6. Excluindo mesa ID {nova_mesa_id}...")
        try:
            response = requests.delete(f"{base_url}/mesas/{nova_mesa_id}", headers=headers)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Mesa excluída: {result['message']}")
            else:
                print(f"❌ Erro ao excluir mesa: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Erro na requisição: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Teste das APIs de Mesa concluído!")

if __name__ == "__main__":
    testar_apis_mesa()
