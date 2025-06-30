# Exemplo de repositório de usuário
from data.db import get_db
from models.user import User

def get_db_global():
    from data.db import get_db
    return get_db(user_email=None)

class UserRepo:
    @staticmethod
    def create_user(user: User):
        db = get_db_global()
        cursor = db.cursor()
        if user.admin_id:
            sql = "INSERT INTO users (name, email, password, role, admin_id) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (user.name, user.email, user.password, user.role, user.admin_id))
        else:
            sql = "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (user.name, user.email, user.password, user.role))
        db.commit()
        cursor.close()
        db.close()

    @staticmethod
    def get_user_by_email(email: str):
        db = get_db_global()
        cursor = db.cursor(dictionary=True)
        sql = "SELECT * FROM users WHERE LOWER(email) = LOWER(%s)"
        cursor.execute(sql, (email,))
        user = cursor.fetchone()
        cursor.close()
        db.close()
        return user

    @staticmethod
    def get_user_by_name(name: str, user_email: str):
        db = get_db(user_email=user_email)
        cursor = db.cursor(dictionary=True)
        sql = "SELECT * FROM users WHERE name = %s"
        cursor.execute(sql, (name,))
        user = cursor.fetchone()
        cursor.close()
        db.close()
        return user

    @staticmethod
    def get_user_by_id(user_id: int):
        db = get_db_global()
        cursor = db.cursor(dictionary=True)
        sql = "SELECT * FROM users WHERE id = %s"
        cursor.execute(sql, (user_id,))
        user = cursor.fetchone()
        cursor.close()
        db.close()
        return user

    @staticmethod
    def listar_usuarios():
        db = get_db_global()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users")
        usuarios = cursor.fetchall()
        cursor.close()
        db.close()
        return usuarios

    @staticmethod
    def excluir_usuario(usuario_id: int):
        db = get_db_global()
        cursor = db.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s AND role = 'garcom'", (usuario_id,))
        db.commit()
        cursor.close()
        db.close()
