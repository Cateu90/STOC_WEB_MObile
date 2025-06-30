-- Migração para permitir NULL em garcom_id na tabela comandas
ALTER TABLE comandas MODIFY garcom_id INT NULL;
