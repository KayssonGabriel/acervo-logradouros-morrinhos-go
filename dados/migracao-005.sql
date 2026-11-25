BEGIN IMMEDIATE;
PRAGMA legacy_alter_table = ON;
CREATE TABLE equivalencia_revisada (
    anterior_id TEXT PRIMARY KEY REFERENCES trecho(id),
    principal_id TEXT NOT NULL REFERENCES trecho(id),
    ato_id TEXT REFERENCES ato_nome(id),
    fonte_postal_id TEXT REFERENCES fonte(id),
    CHECK (anterior_id <> principal_id),
    CHECK ((ato_id IS NULL) <> (fonte_postal_id IS NULL))
);
INSERT INTO equivalencia_revisada (anterior_id, principal_id, ato_id)
SELECT anterior_id, principal_id, ato_id FROM equivalencia_trecho;
DROP TABLE equivalencia_trecho;
ALTER TABLE equivalencia_revisada RENAME TO equivalencia_trecho;
PRAGMA legacy_alter_table = OFF;
CREATE INDEX equivalencia_por_principal ON equivalencia_trecho (principal_id);
PRAGMA user_version = 5;
COMMIT;
