#!/usr/bin/env python3
"""
Script para criar um usuário garçom de teste
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from repo.user_repo import UserRepo
from models.user import User
from util.auth import hash_password
from util.network_info import get_ip_and_port

def criar_usuario_teste():
    email = "garcom@teste.com"
    senha = "123456"
    nome = "Garçom Teste"
    role = "garcom"
    
    # Detecta IP automaticamente
    ip, porta = get_ip_and_port()
    
    print(f"🔄 Criando usuário de teste...")
    print(f"📧 Email: {email}")
    print(f"🔐 Senha: {senha}")
    print(f"👤 Nome: {nome}")
    print(f"🎭 Role: {role}")
    
    # Verificar se já existe
    usuario_existente = UserRepo.get_user_by_email(email)
    if usuario_existente:
        print(f"⚠️  Usuário já existe!")
        print(f"✅ Usuário já configurado corretamente.")
    else:
        # Criar novo usuário
        senha_hash = hash_password(senha)
        user = User(
            name=nome,
            email=email,
            password=senha_hash,
            role=role
        )
        
        try:
            UserRepo.create_user(user)
            print(f"✅ Usuário criado com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao criar usuário: {e}")
            return
    
    print(f"\n" + "="*50)
    print(f"🎉 CONFIGURAÇÃO PARA O APP FLUTTER:")
    print(f"="*50)
    print(f"📱 Configure no app:")
    print(f"   🌐 IP:Porta: http://{ip}:{porta}/api")
    print(f"   📧 Email: {email}")
    print(f"   🔐 Senha: {senha}")
    print(f"="*50)
    print(f"💡 O IP foi detectado automaticamente!")
    print(f"   Se não funcionar, verifique se estão na mesma rede Wi-Fi")
    print(f"="*50)

if __name__ == "__main__":
    criar_usuario_teste()
