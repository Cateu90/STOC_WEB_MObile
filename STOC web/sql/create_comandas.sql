-- Tabela de mesas
CREATE TABLE IF NOT EXISTS mesas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    numero INT NOT NULL,
    status ENUM('livre', 'ocupada') NOT NULL DEFAULT 'livre'
);

-- Tabela de comandas
CREATE TABLE IF NOT EXISTS comandas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mesa_id INT NOT NULL,
    garcom_id INT NOT NULL,
    status ENUM('aberta', 'fechada') NOT NULL DEFAULT 'aberta',
    total DECIMAL(10,2) NOT NULL DEFAULT 0.0,
    FOREIGN KEY (mesa_id) REFERENCES mesas(id),
    FOREIGN KEY (garcom_id) REFERENCES users(id)
);

-- Tabela de itens da comanda
CREATE TABLE IF NOT EXISTS itens_comanda (
    id INT AUTO_INCREMENT PRIMARY KEY,
    comanda_id INT NOT NULL,
    produto_id INT NOT NULL,
    quantidade INT NOT NULL,
    preco_unitario DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (comanda_id) REFERENCES comandas(id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
);
