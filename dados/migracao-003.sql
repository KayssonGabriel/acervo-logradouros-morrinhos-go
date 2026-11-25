BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS mudanca_local (
    id TEXT PRIMARY KEY,
    trecho_id TEXT NOT NULL REFERENCES trecho(id),
    nome_anterior TEXT,
    anterior_chave TEXT,
    nome_novo TEXT,
    novo_chave TEXT,
    vigencia_desde TEXT,
    situacao_cep TEXT NOT NULL CHECK (situacao_cep IN ('alterado', 'mantido', 'desconhecido')),
    cep_anterior TEXT,
    cep_novo TEXT,
    fonte TEXT NOT NULL,
    url_fonte TEXT,
    registrado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (nome_anterior IS NULL OR nome_novo IS NOT NULL),
    CHECK (nome_novo IS NOT NULL OR situacao_cep = 'alterado'),
    CHECK ((situacao_cep = 'alterado' AND cep_novo IS NOT NULL AND cep_novo IS NOT cep_anterior)
        OR (situacao_cep = 'mantido' AND cep_anterior IS NOT NULL AND cep_novo IS NOT NULL AND cep_novo = cep_anterior)
        OR (situacao_cep = 'desconhecido' AND cep_novo IS NULL))
);

CREATE INDEX IF NOT EXISTS mudanca_local_trecho ON mudanca_local (trecho_id, vigencia_desde);
CREATE INDEX IF NOT EXISTS mudanca_local_cep_anterior ON mudanca_local (cep_anterior, trecho_id);
CREATE INDEX IF NOT EXISTS mudanca_local_cep_novo ON mudanca_local (cep_novo, trecho_id);

CREATE VIEW IF NOT EXISTS mudanca_local_v1 AS
SELECT m.*, coalesce(e.principal_id, m.trecho_id) AS trecho_canonico_id
FROM mudanca_local m LEFT JOIN equivalencia_trecho e ON e.anterior_id = m.trecho_id;

CREATE VIEW IF NOT EXISTS nomes_acervo_v1 AS
SELECT trecho_canonico_id AS trecho_id, nome_chave FROM observacao_postal_v1
UNION ALL SELECT trecho_id, anterior_chave FROM ato_nome WHERE anterior_chave IS NOT NULL
UNION ALL SELECT trecho_id, atribuido_chave FROM ato_nome
UNION ALL SELECT trecho_canonico_id, anterior_chave FROM mudanca_local_v1 WHERE anterior_chave IS NOT NULL
UNION ALL SELECT trecho_canonico_id, novo_chave FROM mudanca_local_v1 WHERE novo_chave IS NOT NULL;

CREATE VIEW IF NOT EXISTS ceps_acervo_v1 AS
SELECT trecho_canonico_id AS trecho_id, cep FROM observacao_postal_v1
UNION ALL SELECT trecho_canonico_id, cep_anterior FROM mudanca_local_v1 WHERE cep_anterior <> '75650-000'
UNION ALL SELECT trecho_canonico_id, cep_novo FROM mudanca_local_v1 WHERE cep_novo <> '75650-000';

PRAGMA user_version = 3;
COMMIT;
