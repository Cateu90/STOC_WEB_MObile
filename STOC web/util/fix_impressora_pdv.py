from data.db import get_db

def ensure_pdv_printer(user_email):
    db = get_db(user_email)
    cursor = db.cursor()
    # 1. Garante categoria PDV
    cursor.execute("SELECT id FROM categorias WHERE nome = 'PDV'")
    row = cursor.fetchone()
    if row:
        categoria_id = row[0]
    else:
        cursor.execute("INSERT INTO categorias (nome) VALUES ('PDV')")
        categoria_id = cursor.lastrowid
        db.commit()
    # 2. Garante impressora
    cursor.execute("SELECT id FROM impressoras LIMIT 1")
    row = cursor.fetchone()
    if row:
        impressora_id = row[0]
    else:
        cursor.execute("INSERT INTO impressoras (nome, setor, printer_name) VALUES ('PDV', 'PDV', 'ImpressoraPDV')")
        impressora_id = cursor.lastrowid
        db.commit()
    # 3. Garante associação
    cursor.execute("SELECT 1 FROM impressora_categorias WHERE impressora_id = %s AND categoria_id = %s", (impressora_id, categoria_id))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO impressora_categorias (impressora_id, categoria_id) VALUES (%s, %s)", (impressora_id, categoria_id))
        db.commit()
    cursor.close()
    db.close()
    print(f"Impressora {impressora_id} associada à categoria PDV ({categoria_id}) para {user_email}")

if __name__ == "__main__":
    # Substitua pelo e-mail do usuário desejado
    user_email = input("Digite o e-mail do usuário para corrigir a impressora PDV: ")
    ensure_pdv_printer(user_email)
    print("Correção concluída!")
