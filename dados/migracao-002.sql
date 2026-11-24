BEGIN IMMEDIATE;
ALTER TABLE fonte ADD COLUMN abrangencia TEXT CHECK (abrangencia IN ('integral', 'complementar'));
UPDATE fonte SET abrangencia = 'integral' WHERE tipo = 'lista_postal';
UPDATE fonte SET abrangencia = 'complementar' WHERE id = 'lista-2025-10';
CREATE INDEX IF NOT EXISTS equivalencia_por_principal ON equivalencia_trecho (principal_id);
DROP VIEW consulta_v1;
CREATE VIEW consulta_v1 AS
WITH versao_integral AS (
    SELECT max(referencia) AS referencia FROM fonte WHERE tipo = 'lista_postal' AND abrangencia = 'integral'
), postal AS (
    SELECT o.*, f.referencia, f.url, f.arquivo, f.abrangencia,
        row_number() OVER (
            PARTITION BY o.trecho_canonico_id
            ORDER BY f.referencia DESC, f.prioridade DESC, f.id, o.pagina, o.linha
        ) AS ordem
    FROM observacao_postal_v1 o JOIN fonte f ON f.id = o.fonte_id
), municipal AS (
    SELECT a.*, row_number() OVER (
        PARTITION BY a.trecho_id ORDER BY coalesce(a.vigencia_desde, f.referencia) DESC, a.id
    ) AS ordem
    FROM ato_nome a JOIN fonte f ON f.id = a.fonte_id
)
SELECT t.id AS trecho_id,
       'Morrinhos' AS municipio, 'GO' AS uf,
       coalesce(p.bairro_original, b.nome) AS bairro,
       b.chave AS bairro_chave,
       m.trecho_no_ato AS trecho_documentado,
       m.nome_atribuido AS nome_municipal_documentado,
       p.nome_original AS nome_postal_publicado,
       p.cep AS cep_publicado, p.fim_anunciado AS fim_uso_geral_anunciado,
       p.fonte_id AS fonte_postal_id, p.referencia AS referencia_postal,
       p.url AS url_fonte_postal, p.pagina AS pagina_fonte_postal,
       p.id AS observacao_postal_id, m.fonte_id AS fonte_municipal_id,
       fm.url AS url_fonte_municipal, m.pagina AS pagina_fonte_municipal,
       CASE
         WHEN t.tipo = 'cep_geral_historico' THEN 'cep_geral_historico'
         WHEN EXISTS (SELECT 1 FROM ato_nome a WHERE a.trecho_id = t.id AND a.nome_anterior IS NOT NULL)
           THEN 'alteracao_documentada'
         WHEN m.id IS NOT NULL THEN 'denominacao_documentada'
         ELSE 'historico_a_confirmar'
       END AS situacao_historico,
       CASE
         WHEN t.tipo = 'cep_geral_historico' THEN 'cep_geral_historico'
         WHEN p.id IS NULL THEN 'sem_cep_nas_fontes'
         WHEN p.referencia < (SELECT referencia FROM versao_integral) THEN 'publicado_lista_anterior'
         WHEN p.abrangencia = 'complementar' THEN 'publicado_lista_complementar'
         ELSE 'publicado_ultima_lista'
       END AS situacao_postal,
       EXISTS (
         SELECT 1 FROM observacao_postal_v1 outra JOIN trecho outro ON outro.id = outra.trecho_id
         WHERE outra.cep = p.cep AND outra.trecho_canonico_id <> t.id AND (
               outra.nome_chave <> p.nome_chave OR outro.bairro_id IS NOT t.bairro_id
         )
        ) AS divergencia_postal,
       p.abrangencia AS abrangencia_fonte_postal,
       coalesce(c.resultado, 'pendente') AS conferencia_correios,
       c.conferido_em, c.endereco_retornado, c.evidencia AS evidencia_conferencia
FROM trecho t
LEFT JOIN bairro b ON b.id = t.bairro_id
LEFT JOIN postal p ON p.trecho_canonico_id = t.id AND p.ordem = 1
LEFT JOIN municipal m ON m.trecho_id = t.id AND m.ordem = 1
LEFT JOIN fonte fm ON fm.id = m.fonte_id
LEFT JOIN conferencia_correios c ON c.id = (
    SELECT id FROM conferencia_correios WHERE observacao_id = p.id
    ORDER BY conferido_em DESC, id DESC LIMIT 1
)
WHERE t.id NOT IN (SELECT anterior_id FROM equivalencia_trecho)
  AND (p.id IS NOT NULL OR m.id IS NOT NULL);

PRAGMA user_version = 2;
COMMIT;
