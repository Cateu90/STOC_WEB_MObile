SELECT c.id, c.total, c.garcom_id, c.status, c.created_at, c.pagamento
FROM comandas c
WHERE c.status = 'fechada' AND c.created_at BETWEEN %s AND %s;

SELECT ic.produto_id, SUM(ic.quantidade) as total_vendido
FROM itens_comanda ic
JOIN comandas c ON ic.comanda_id = c.id
WHERE c.status = 'fechada' AND c.created_at BETWEEN %s AND %s
GROUP BY ic.produto_id
ORDER BY total_vendido DESC;

SELECT c.garcom_id, COUNT(*) as comandas, SUM(c.total) as total_vendas
FROM comandas c
WHERE c.status = 'fechada' AND c.created_at BETWEEN %s AND %s
GROUP BY c.garcom_id
ORDER BY total_vendas DESC;
