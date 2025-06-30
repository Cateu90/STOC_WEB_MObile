import sys
import os

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from data.db import get_db, get_all_user_dbs
import mysql.connector

def executar_migracao_impressora_pdv():
    """
    Garante que para cada banco de usuário, exista uma impressora 'CAIXA'
    e que ela esteja associada à categoria 'PDV'.
    """
    logging.basicConfig(level=logging.INFO)
    
    user_dbs = get_all_user_dbs()
    if not user_dbs:
        logging.info("Nenhum banco de dados de usuário encontrado para migração.")
        return

    for db_name in user_dbs:
        db = None # Inicializa db como None
        try:
            logging.info(f"Verificando migração para o banco de dados: {db_name}")
            db = get_db(db_name=db_name) # Conecta ao banco de dados completo
            cursor = db.cursor(dictionary=True)

            # 1. Verificar se a categoria PDV existe
            cursor.execute("SELECT id FROM categorias WHERE nome = 'PDV'")
            categoria_pdv = cursor.fetchone()
            if not categoria_pdv:
                logging.warning(f"Categoria 'PDV' não encontrada em {db_name}. Pulando.")
                continue
            
            categoria_pdv_id = categoria_pdv['id']

            # 2. Verificar se a impressora 'CAIXA' existe
            cursor.execute("SELECT id FROM impressoras WHERE nome = 'CAIXA'")
            impressora_caixa = cursor.fetchone()
            
            if impressora_caixa:
                impressora_caixa_id = impressora_caixa['id']
                logging.info(f"Impressora 'CAIXA' já existe em {db_name} com ID {impressora_caixa_id}.")
            else:
                # 3. Se não existir, criar a impressora 'CAIXA'
                cursor.execute("INSERT INTO impressoras (nome, setor, printer_name) VALUES (%s, %s, %s)", 
                               ("CAIXA", "Caixa", "CAIXA"))
                impressora_caixa_id = cursor.lastrowid
                logging.info(f"Impressora 'CAIXA' criada em {db_name} com ID {impressora_caixa_id}.")

            # 4. Verificar se a associação entre Impressora CAIXA e Categoria PDV existe
            cursor.execute("""
                SELECT * FROM impressora_categorias 
                WHERE impressora_id = %s AND categoria_id = %s
            """, (impressora_caixa_id, categoria_pdv_id))
            
            associacao = cursor.fetchone()

            if associacao:
                logging.info(f"Associação entre Impressora CAIXA e Categoria PDV já existe em {db_name}.")
            else:
                # 5. Se não existir, criar a associação
                cursor.execute("""
                    INSERT INTO impressora_categorias (impressora_id, categoria_id) 
                    VALUES (%s, %s)
                """, (impressora_caixa_id, categoria_pdv_id))
                logging.info(f"Associação entre Impressora CAIXA e Categoria PDV criada em {db_name}.")

            db.commit()
            logging.info(f"Migração concluída com sucesso para {db_name}.")

        except mysql.connector.Error as err:
            logging.error(f"Erro de banco de dados durante a migração para {db_name}: {err}")
            if db and db.is_connected():
                db.rollback()
        except Exception as e:
            logging.error(f"Erro inesperado durante a migração para {db_name}: {e}")
        finally:
            if db and db.is_connected():
                cursor.close()
                db.close()

if __name__ == "__main__":
    executar_migracao_impressora_pdv()
