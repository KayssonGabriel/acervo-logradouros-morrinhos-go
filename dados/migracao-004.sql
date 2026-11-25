BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS nome_historico (
    id TEXT PRIMARY KEY,
    trecho_id TEXT NOT NULL REFERENCES trecho(id),
    nome TEXT NOT NULL,
    nome_chave TEXT NOT NULL,
    ano INTEGER,
    fonte_id TEXT NOT NULL,
    fonte TEXT NOT NULL,
    url TEXT NOT NULL,
    pagina INTEGER NOT NULL CHECK (pagina > 0),
    pagina_correspondencia INTEGER NOT NULL CHECK (pagina_correspondencia > 0),
    nota TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS nome_historico_trecho ON nome_historico(trecho_id);

CREATE VIEW IF NOT EXISTS nome_historico_v1 AS
SELECT h.*, coalesce(e.principal_id, h.trecho_id) AS trecho_canonico_id
FROM nome_historico h LEFT JOIN equivalencia_trecho e ON e.anterior_id = h.trecho_id;

CREATE VIEW IF NOT EXISTS nomes_acervo_v2 AS
SELECT trecho_id, nome_chave FROM nomes_acervo_v1
UNION ALL SELECT trecho_canonico_id, nome_chave FROM nome_historico_v1;

PRAGMA user_version = 4;
COMMIT;
