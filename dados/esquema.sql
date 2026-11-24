CREATE TABLE IF NOT EXISTS fonte (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL CHECK (tipo IN ('lista_postal', 'lei_municipal', 'comunicado')),
    referencia TEXT NOT NULL,
    arquivo TEXT,
    url TEXT NOT NULL,
    sha256 TEXT,
    prioridade INTEGER NOT NULL DEFAULT 0,
    nota TEXT
);

CREATE TABLE IF NOT EXISTS bairro (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    chave TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS trecho (
    id TEXT PRIMARY KEY,
    bairro_id INTEGER REFERENCES bairro(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('registro_postal', 'trecho_de_lei', 'cep_geral_historico'))
);

CREATE TABLE IF NOT EXISTS observacao_postal (
    id INTEGER PRIMARY KEY,
    trecho_id TEXT NOT NULL REFERENCES trecho(id),
    fonte_id TEXT NOT NULL REFERENCES fonte(id),
    pagina INTEGER NOT NULL CHECK (pagina > 0),
    linha INTEGER NOT NULL CHECK (linha > 0),
    nome_original TEXT NOT NULL,
    nome_chave TEXT NOT NULL,
    bairro_original TEXT,
    cep_original TEXT NOT NULL,
    cep TEXT NOT NULL CHECK (cep GLOB '[0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9]'),
    fim_anunciado TEXT,
    UNIQUE (fonte_id, pagina, linha)
);

CREATE TABLE IF NOT EXISTS ato_nome (
    id TEXT PRIMARY KEY,
    trecho_id TEXT NOT NULL REFERENCES trecho(id),
    fonte_id TEXT NOT NULL REFERENCES fonte(id),
    numero TEXT NOT NULL,
    artigo TEXT NOT NULL,
    pagina INTEGER NOT NULL CHECK (pagina > 0),
    bairro_no_ato TEXT NOT NULL,
    trecho_no_ato TEXT,
    nome_anterior TEXT,
    anterior_chave TEXT,
    nome_atribuido TEXT NOT NULL,
    atribuido_chave TEXT NOT NULL,
    data_publicacao TEXT,
    vigencia_desde TEXT,
    nota TEXT
);

CREATE TABLE IF NOT EXISTS conferencia_correios (
    id INTEGER PRIMARY KEY,
    observacao_id INTEGER NOT NULL REFERENCES observacao_postal(id),
    conferido_em TEXT NOT NULL,
    responsavel TEXT NOT NULL,
    resultado TEXT NOT NULL CHECK (resultado IN ('confirmado', 'divergente', 'nao_localizado')),
    endereco_retornado TEXT,
    evidencia TEXT NOT NULL,
    CHECK (resultado = 'nao_localizado' OR length(trim(coalesce(endereco_retornado, ''))) > 0)
);

CREATE TABLE IF NOT EXISTS equivalencia_trecho (
    anterior_id TEXT PRIMARY KEY REFERENCES trecho(id),
    principal_id TEXT NOT NULL REFERENCES trecho(id),
    ato_id TEXT NOT NULL REFERENCES ato_nome(id),
    CHECK (anterior_id <> principal_id)
);

CREATE INDEX IF NOT EXISTS observacao_cep ON observacao_postal (cep, trecho_id);
CREATE INDEX IF NOT EXISTS observacao_trecho ON observacao_postal (trecho_id, fonte_id);
CREATE INDEX IF NOT EXISTS ato_trecho ON ato_nome (trecho_id, fonte_id);
CREATE INDEX IF NOT EXISTS conferencia_observacao ON conferencia_correios (observacao_id, conferido_em);

CREATE VIEW IF NOT EXISTS observacao_postal_v1 AS
SELECT o.*, coalesce(e.principal_id, o.trecho_id) AS trecho_canonico_id
FROM observacao_postal o LEFT JOIN equivalencia_trecho e ON e.anterior_id = o.trecho_id;

CREATE VIEW IF NOT EXISTS consulta_v1 AS
WITH postal AS (
    SELECT o.*, f.referencia, f.url, f.arquivo,
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
         WHEN p.referencia < (SELECT max(referencia) FROM fonte WHERE tipo = 'lista_postal')
           THEN 'publicado_lista_anterior'
         ELSE 'publicado_ultima_lista'
       END AS situacao_postal,
       EXISTS (
         SELECT 1 FROM observacao_postal_v1 outra JOIN trecho outro ON outro.id = outra.trecho_id
         WHERE outra.cep = p.cep AND outra.trecho_canonico_id <> t.id AND (
               outra.nome_chave <> p.nome_chave OR outro.bairro_id IS NOT t.bairro_id
         )
       ) AS divergencia_postal,
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

PRAGMA user_version = 1;
