import os
from data.db import get_db

def executar_sqls_iniciais(sql_dir="sql", user_email=None):
    db = get_db(user_email=user_email)
    cursor = db.cursor()
    for filename in sorted(os.listdir(sql_dir)):
        if filename.endswith(".sql"):
            path = os.path.join(sql_dir, filename)
            with open(path, encoding="utf-8") as f:
                sql = f.read()
                for statement in sql.split(';'):
                    stmt = statement.strip()
                    if stmt:
                        try:
                            cursor.execute(stmt)
                            if stmt.lower().startswith("select"):
                                cursor.fetchall()
                        except Exception as e:
                            print(f"[SQL INIT] Erro ao executar {filename}: {e}")
                        else:
                            print(f"[SQL INIT] Executado com sucesso: {filename}")
    # Remover a criação automática da impressora padrão "CAIXA"
    # try:
    #     cursor.execute("INSERT INTO impressoras (nome, setor) VALUES (%s, %s)", ("CAIXA", "Caixa"))
    #     impressora_id = cursor.lastrowid
    #     cursor.execute("UPDATE categorias SET impressora_id = %s WHERE nome = %s", (impressora_id, "PDV"))
    #     db.commit()
    #     print(f"Impressora CAIXA criada e associada à categoria PDV no banco de dados.")
    # except Exception as err:
    #     print(f"Erro ao configurar impressora padrão: {err}")
    #     db.rollback()
    # finally:
    #     cursor.close()
    #     db.close()

    # Adicionar usuário PDV
    try:
        db = get_db(user_email=user_email)
        cursor = db.cursor()
        
        # Verificar se o usuário PDV já existe
        cursor.execute("SELECT id FROM users WHERE name = %s", ("PDV",))
        if cursor.fetchone():
            print("Usuário PDV já existe.")
        else:
            from util.auth import hash_password
            hashed_password = hash_password("pdv")
            cursor.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)", ("PDV", "pdv@system.com", hashed_password, "garcom"))
            db.commit()
            print(f"Usuário PDV criado no banco de dados.")
            
    except Exception as err:
        print(f"Erro ao criar/verificar usuário PDV: {err}")
        db.rollback()
    finally:
        if 'db' in locals() and db.is_connected():
            cursor.close()
            db.close()
