-- Adicionar coluna descricao na tabela produtos se não existir
ALTER TABLE produtos ADD COLUMN IF NOT EXISTS descricao TEXT;
