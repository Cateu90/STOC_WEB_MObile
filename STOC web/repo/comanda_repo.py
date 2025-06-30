# Repositório de comanda
from data.db import get_db
from models.comanda import Comanda

class ComandaRepo:
    @staticmethod
    def abrir_comanda(comanda: Comanda, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor()
        # Modificado para não inserir total e pagamento na abertura
        sql = "INSERT INTO comandas (mesa_id, garcom_id, status) VALUES (%s, %s, %s)"
        cursor.execute(sql, (comanda.mesa_id, comanda.garcom_id, comanda.status))
        comanda_id = cursor.lastrowid
        db.commit()
        cursor.close()
        db.close()
        return comanda_id

    @staticmethod
    def listar_comandas_abertas(user_email=None, garcom_id=None):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        if garcom_id:
            cursor.execute("""
                SELECT 
                    c.*,
                    m.numero as mesa_numero
                FROM comandas c
                LEFT JOIN mesas m ON c.mesa_id = m.id
                WHERE c.status = 'aberta' AND c.garcom_id = %s
                ORDER BY c.created_at DESC
            """, (garcom_id,))
        else:
            cursor.execute("""
                SELECT 
                    c.*,
                    m.numero as mesa_numero
                FROM comandas c
                LEFT JOIN mesas m ON c.mesa_id = m.id
                WHERE c.status = 'aberta'
                ORDER BY c.created_at DESC
            """)
        comandas = cursor.fetchall()
        cursor.close()
        db.close()
        return comandas

    @staticmethod
    def listar_comandas_por_garcom(garcom_id: int, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                c.*,
                m.numero as mesa_numero
            FROM comandas c
            LEFT JOIN mesas m ON c.mesa_id = m.id
            WHERE c.garcom_id = %s AND c.status = 'aberta'
        """, (garcom_id,))
        comandas = cursor.fetchall()
        cursor.close()
        db.close()
        return comandas

    @staticmethod
    def listar_todas_comandas(user_email=None):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                c.*,
                m.numero as mesa_numero
            FROM comandas c
            LEFT JOIN mesas m ON c.mesa_id = m.id
            ORDER BY c.created_at DESC
        """)
        comandas = cursor.fetchall()
        cursor.close()
        db.close()
        return comandas

    @staticmethod
    def fechar_comanda(comanda_id: int, total: float, pagamento: str, user_email=None, db=None, cursor=None):
        own_connection = False
        if db is None or cursor is None:
            db = get_db(user_email)
            cursor = db.cursor()
            own_connection = True
        sql = "UPDATE comandas SET status = 'fechada', total = %s, pagamento = %s WHERE id = %s"
        cursor.execute(sql, (total, pagamento, comanda_id))
        if own_connection:
            db.commit()
            cursor.close()
            db.close()
