import os
from data.db import get_db

def executar_sqls_iniciais(sql_dir="sql"):
    """Executa scripts SQL de inicialização no banco principal"""
    db = get_db()
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
    db.commit()
    cursor.close()
    db.close()

def inicializar_banco_usuario(user_email):
    """Inicializa o banco de dados específico do usuário com a estrutura necessária"""
    try:
        # Primeiro, garantir que o banco do usuário existe
        from data.db import ensure_user_database_exists
        ensure_user_database_exists(user_email)
        
        db = get_db(user_email)
        cursor = db.cursor()
        
        # Verificar se as tabelas já existem
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        # Sempre garantir que as tabelas de impressoras existem
        impressoras_existe = 'impressoras' in table_names
        impressora_categorias_existe = 'impressora_categorias' in table_names
        
        # Se não há tabelas, criar a estrutura manualmente
        if not table_names:
            print(f"[USER DB INIT] Criando estrutura completa para usuário: {user_email}")
            
            # Criar tabelas manualmente para garantir ordem correta
            
            # 1. Tabela de categorias
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categorias (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    impressora_id INT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 2. Tabela de produtos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS produtos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    preco DECIMAL(10,2) NOT NULL,
                    categoria_id INT,
                    tipo VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
                )
            """)
            
            # 3. Tabela de mesas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mesas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    numero INT NOT NULL,
                    capacidade INT DEFAULT 4,
                    status VARCHAR(50) DEFAULT 'livre',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 4. Tabela de comandas (sem referência de chave estrangeira para garcom_id)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comandas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    mesa_id INT NULL,
                    garcom_id INT NULL,
                    status VARCHAR(50) DEFAULT 'aberta',
                    total DECIMAL(10,2) DEFAULT 0,
                    pagamento VARCHAR(100) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mesa_id) REFERENCES mesas(id)
                )
            """)
            
            # 5. Tabela de itens da comanda
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS itens_comanda (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    comanda_id INT NOT NULL,
                    produto_id INT NOT NULL,
                    quantidade INT NOT NULL,
                    preco_unitario DECIMAL(10,2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (comanda_id) REFERENCES comandas(id),
                    FOREIGN KEY (produto_id) REFERENCES produtos(id)
                )
            """)
            
            # 6. Tabela de impressoras
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS impressoras (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    setor VARCHAR(255) NOT NULL,
                    printer_name VARCHAR(255) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 7. Tabela de associação impressora_categorias
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS impressora_categorias (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    impressora_id INT NOT NULL,
                    categoria_id INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (impressora_id) REFERENCES impressoras(id) ON DELETE CASCADE,
                    FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_impressora_categoria (impressora_id, categoria_id)
                )
            """)
            
            print(f"[USER DB INIT] Tabelas criadas para usuário: {user_email}")
        
        # Sempre garantir que as tabelas de impressoras existem (mesmo se outras tabelas já existem)
        if not impressoras_existe:
            print(f"[USER DB INIT] Criando tabela 'impressoras' para usuário: {user_email}")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS impressoras (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    setor VARCHAR(255) NOT NULL,
                    printer_name VARCHAR(255) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        if not impressora_categorias_existe:
            print(f"[USER DB INIT] Criando tabela 'impressora_categorias' para usuário: {user_email}")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS impressora_categorias (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    impressora_id INT NOT NULL,
                    categoria_id INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (impressora_id) REFERENCES impressoras(id) ON DELETE CASCADE,
                    FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_impressora_categoria (impressora_id, categoria_id)
                )
            """)
        
        # Criar categorias fixas para o usuário (se ainda não existem)
        try:
            cursor.execute("SELECT COUNT(*) FROM categorias")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO categorias (nome, impressora_id) VALUES 
                    ('Bebidas', NULL),
                    ('Entradas', NULL),
                    ('Prato Principal', NULL),
                    ('Sobremesas', NULL),
                    ('Outros', NULL),
                    ('PDV', NULL)
                """)
                print(f"[USER DB INIT] Categorias fixas criadas para usuário: {user_email}")
        except Exception as e:
            print(f"[USER DB INIT] Erro ao criar categorias: {e}")
            
            # Criar pelo menos uma mesa padrão
            try:
                cursor.execute("SELECT COUNT(*) FROM mesas")
                if cursor.fetchone()[0] == 0:
                    cursor.execute("INSERT INTO mesas (numero, capacidade, status) VALUES (1, 4, 'livre')")
                    print(f"[USER DB INIT] Mesa padrão criada para usuário: {user_email}")
            except Exception as e:
                print(f"[USER DB INIT] Erro ao criar mesa padrão: {e}")
            
            # Criar produtos de exemplo se não existirem
            try:
                cursor.execute("SELECT COUNT(*) FROM produtos")
                if cursor.fetchone()[0] == 0:
                    # Criar produtos manualmente usando IDs das categorias
                    cursor.execute("SELECT id FROM categorias WHERE nome = 'Bebidas'")
                    bebidas_id = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT id FROM categorias WHERE nome = 'Prato Principal'")
                    prato_id = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT id FROM categorias WHERE nome = 'Entradas'")
                    entrada_id = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT id FROM categorias WHERE nome = 'Outros'")
                    outros_id = cursor.fetchone()[0]
                    
                    produtos_exemplo = [
                        ('Refrigerante Coca-Cola', 5.50, bebidas_id, 'bebida'),
                        ('Hambúrguer Clássico', 18.90, prato_id, 'lanche'),
                        ('Batata Frita', 12.50, entrada_id, 'acompanhamento'),
                        ('Água Mineral', 3.00, bebidas_id, 'bebida'),
                        ('Suco Natural Laranja', 7.50, bebidas_id, 'bebida'),
                        ('Pizza Margherita', 32.90, prato_id, 'prato principal'),
                        ('Café Expresso', 4.50, bebidas_id, 'bebida'),
                        ('Pastel de Queijo', 8.90, entrada_id, 'lanche'),
                        ('Cerveja Long Neck', 7.90, bebidas_id, 'bebida'),
                        ('Sanduíche Natural', 14.50, outros_id, 'lanche')
                    ]
                    
                    for produto in produtos_exemplo:
                        cursor.execute(
                            "INSERT INTO produtos (nome, preco, categoria_id, tipo) VALUES (%s, %s, %s, %s)",
                            produto
                        )
                    
                    print(f"[USER DB INIT] Produtos de exemplo criados para usuário: {user_email}")
            except Exception as e:
                print(f"[USER DB INIT] Erro ao criar produtos exemplo: {e}")
        
        db.commit()
        cursor.close()
        db.close()
        
        print(f"[USER DB INIT] Banco inicializado com sucesso para usuário: {user_email}")
        return True
        
    except Exception as e:
        print(f"[USER DB INIT] Erro ao inicializar banco do usuário {user_email}: {e}")
        import traceback
        traceback.print_exc()
        return False
