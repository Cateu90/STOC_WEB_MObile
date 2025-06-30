-- Adiciona campo 'ativo' à tabela produtos
ALTER TABLE produtos ADD COLUMN ativo TINYINT(1) NOT NULL DEFAULT 1;

-- Atualiza todos os produtos existentes para ativos
UPDATE produtos SET ativo = 1;
