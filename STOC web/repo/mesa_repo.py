# Repositório de mesa
from data.db import get_db
from models.mesa import Mesa

class MesaRepo:
    @staticmethod
    def listar_mesas(user_email=None):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM mesas")
        mesas = cursor.fetchall()
        cursor.close()
        db.close()
        return mesas
