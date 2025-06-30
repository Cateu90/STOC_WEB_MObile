#!/usr/bin/env python3
"""
Script para testar o login do garçom sem mesas cadastradas
"""

import sys
import os

# Adiciona o diretório do projeto ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from repo.user_repo import UserRepo
from models.user import User
from util.auth import hash_password
from util.network_info import get_ip_and_port

def criar_garcom_teste():
    """Cria um usuário garçom de teste"""
    
    email = "garcom@teste.com"
    password = "123456"
    nome = "Garçom Teste"
    
    # Verificar se o usuário já existe
    user_existente = UserRepo.get_user_by_email(email)
    if user_existente:
        print(f"✅ Usuário garçom já existe: {email}")
        return user_existente
    
    try:
        # Criar usuário garçom
        hashed_password = hash_password(password)
        user = User(
            name=nome,
            email=email,
            password=hashed_password,
            role="garcom"
        )
        
        UserRepo.create_user(user)
        print(f"✅ Usuário garçom criado com sucesso!")
        print(f"📧 Email: {email}")
        print(f"🔑 Senha: {password}")
        
        return UserRepo.get_user_by_email(email)
        
    except Exception as e:
        print(f"❌ Erro ao criar usuário garçom: {e}")
        return None

def testar_ambiente_garcom():
    """Testa o ambiente do garçom"""
    
    email = "garcom@teste.com"
    
    try:
        from data.db import ensure_user_database_exists
        from util.init_db import executar_sqls_iniciais
        
        print(f"🔧 Testando ambiente para garçom: {email}")
        
        # Garantir que o banco de dados existe
        ensure_user_database_exists(email)
        print("✅ Banco de dados criado/verificado")
        
        # Executar SQLs iniciais
        executar_sqls_iniciais("sql", user_email=email)
        print("✅ SQLs iniciais executados")
        
        # Verificar mesas (sem criar)
        from repo.mesa_repo import MesaRepo
        mesas = MesaRepo.listar_mesas(user_email=email)
        print(f"📋 Mesas existentes: {len(mesas)}")
        
        if len(mesas) == 0:
            print("✅ Nenhuma mesa encontrada - garçom pode cadastrar pelo app")
        else:
            for mesa in mesas:
                print(f"   - {mesa['nome']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar ambiente: {e}")
        return False

def main():
    print("🧪 TESTANDO LOGIN DO GARÇOM SEM MESAS")
    print("=" * 50)
    
    # Criar usuário garçom
    user = criar_garcom_teste()
    if not user:
        print("❌ Falha ao criar usuário garçom")
        return
    
    print()
    print("🔧 TESTANDO AMBIENTE...")
    print("-" * 30)
    
    # Testar ambiente
    if testar_ambiente_garcom():
        print("✅ Ambiente configurado com sucesso")
    else:
        print("❌ Falha ao configurar ambiente")
        return
    
    print()
    print("📱 INSTRUÇÕES PARA TESTE NO APP:")
    print("-" * 40)
    
    # Obter IP e porta
    ip, port = get_ip_and_port()
    
    print(f"1. Configure o app Flutter para usar:")
    print(f"   http://{ip}:{port}/api")
    print()
    print(f"2. Faça login com:")
    print(f"   📧 Email: garcom@teste.com")
    print(f"   🔑 Senha: 123456")
    print()
    print(f"3. O garçom deve conseguir fazer login mesmo sem mesas")
    print(f"4. Após o login, ele pode cadastrar mesas pelo app")
    print()
    print("✅ Teste concluído!")

if __name__ == "__main__":
    main()
