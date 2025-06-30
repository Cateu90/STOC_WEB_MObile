import sys
import os

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.db import get_all_user_dbs, get_db
from util.auth import hash_password

def migrar_usuario_pdv():
    """Garante que o usuário 'PDV' exista em todos os bancos de dados de usuários."""
    user_dbs = get_all_user_dbs()
    print(f"Bancos de dados encontrados: {user_dbs}")

    for db_name in user_dbs:
        print(f"\nProcessando banco de dados: {db_name}")
        try:
            db = get_db(db_name=db_name)
            cursor = db.cursor()

            # 1. Verificar se o usuário 'PDV' já existe
            cursor.execute("SELECT id FROM users WHERE name = %s", ("PDV",))
            if cursor.fetchone():
                print(f"Usuário 'PDV' já existe em '{db_name}'.")
                cursor.close()
                db.close()
                continue

            # 2. Se não existir, criar o usuário 'PDV'
            print(f"Criando usuário 'PDV' em '{db_name}'...")
            hashed_pdv_password = hash_password("pdv") # Senha padrão, pode ser alterada
            cursor.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                ("PDV", "pdv@system.com", hashed_pdv_password, "garcom")
            )
            db.commit()
            print(f"Usuário 'PDV' criado com sucesso em '{db_name}'.")

            cursor.close()
            db.close()

        except Exception as e:
            print(f"Erro ao processar o banco de dados {db_name}: {e}")

if __name__ == "__main__":
    migrar_usuario_pdv()
