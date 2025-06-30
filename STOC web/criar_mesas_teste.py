#!/usr/bin/env python3
"""
Script para criar mesas de teste
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from repo.mesa_repo import MesaRepo
from models.mesa import Mesa

def criar_mesas_teste():
    user_email = "garcom@teste.com"
    
    print(f"🔄 Criando mesas de teste para {user_email}...")
    
    # Verificar quantas mesas já existem
    mesas_existentes = MesaRepo.listar_mesas(user_email=user_email)
    print(f"📊 Mesas existentes: {len(mesas_existentes)}")
    
    if len(mesas_existentes) >= 10:
        print(f"✅ Já existem {len(mesas_existentes)} mesas. Não é necessário criar mais.")
        return
    
    # Criar mesas de 1 a 10
    mesas_criadas = 0
    for i in range(1, 11):
        nome_mesa = f"Mesa {i:02d}"
        
        # Verificar se a mesa já existe
        mesa_existe = any(mesa['nome'] == nome_mesa for mesa in mesas_existentes)
        if mesa_existe:
            print(f"⚠️  {nome_mesa} já existe, pulando...")
            continue
        
        try:
            mesa = Mesa(
                nome=nome_mesa,
                user_email=user_email
            )
            MesaRepo.inserir_mesa(mesa)
            mesas_criadas += 1
            print(f"✅ {nome_mesa} criada com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao criar {nome_mesa}: {e}")
    
    print(f"\n🎉 Processo concluído!")
    print(f"📊 Mesas criadas nesta execução: {mesas_criadas}")
    
    # Listar todas as mesas
    mesas_finais = MesaRepo.listar_mesas(user_email=user_email)
    print(f"📊 Total de mesas disponíveis: {len(mesas_finais)}")
    
    if mesas_finais:
        print("\n📋 Mesas disponíveis:")
        for mesa in mesas_finais:
            print(f"   🏷️  {mesa['nome']} (ID: {mesa['id']})")

if __name__ == "__main__":
    criar_mesas_teste()
