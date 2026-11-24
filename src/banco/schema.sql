-- Esquema usado por PostgresManutencaoRepositorio.
-- Executar este arquivo de novo apaga e recria as tabelas, eliminando os dados.

DROP TABLE IF EXISTS notificacao, registro_auditoria, chamado_tecnico, chamado,
    equipamento, usuario, departamento CASCADE;
DROP FUNCTION IF EXISTS impedir_alteracao_auditoria();

CREATE TABLE departamento (
    id   INTEGER PRIMARY KEY,
    nome TEXT NOT NULL
);

CREATE TABLE usuario (
    id              INTEGER PRIMARY KEY,
    nome            TEXT NOT NULL,
    email           TEXT NOT NULL,
    papel           TEXT NOT NULL
        CHECK (papel IN ('SOLICITANTE', 'TECNICO', 'COORDENADOR')),
    departamento_id INTEGER REFERENCES departamento (id)
);

CREATE TABLE equipamento (
    id              INTEGER PRIMARY KEY,
    nome            TEXT NOT NULL,
    laboratorio     TEXT NOT NULL,
    departamento_id INTEGER NOT NULL REFERENCES departamento (id)
);

CREATE TABLE chamado (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    equipamento_id          INTEGER NOT NULL REFERENCES equipamento (id),
    solicitante_id          INTEGER NOT NULL REFERENCES usuario (id),
    departamento_id         INTEGER NOT NULL REFERENCES departamento (id),
    descricao_problema      TEXT NOT NULL CHECK (btrim(descricao_problema) <> ''),
    informacoes_adicionais  TEXT NOT NULL DEFAULT '',
    data_ocorrencia         DATE NOT NULL,
    data_abertura           TIMESTAMP NOT NULL,
    estado                  TEXT NOT NULL
        CHECK (estado IN ('ABERTO', 'ATRIBUIDO', 'EM_ATENDIMENTO', 'CONCLUIDO')),
    prioridade              TEXT
        CHECK (prioridade IN ('BAIXA', 'MEDIA', 'ALTA', 'URGENTE', 'CRITICA')),
    data_inicio_atendimento TIMESTAMP,
    diagnostico             TEXT,
    descricao_intervencao   TEXT,
    concluido_por_id        INTEGER REFERENCES usuario (id),
    data_conclusao          TIMESTAMP
);

-- Técnicos atribuídos aos chamados em uma relação muitos para muitos.
CREATE TABLE chamado_tecnico (
    chamado_id INTEGER NOT NULL REFERENCES chamado (id),
    tecnico_id INTEGER NOT NULL REFERENCES usuario (id),
    PRIMARY KEY (chamado_id, tecnico_id)
);

CREATE TABLE registro_auditoria (
    id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chamado_id     INTEGER NOT NULL REFERENCES chamado (id),
    autor_id       INTEGER NOT NULL REFERENCES usuario (id),
    data_hora      TIMESTAMP NOT NULL,
    campo          TEXT NOT NULL,
    valor_anterior TEXT,
    valor_novo     TEXT,
    observacao     TEXT NOT NULL DEFAULT ''
);

-- Protege o histórico de auditoria contra alterações e exclusões via SQL (ASR01).
CREATE FUNCTION impedir_alteracao_auditoria() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'registro_auditoria is append-only (ASR01)';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auditoria_somente_insercao
    BEFORE UPDATE OR DELETE ON registro_auditoria
    FOR EACH ROW EXECUTE FUNCTION impedir_alteracao_auditoria();

-- Fila de e-mails (ASR03). O agendador processa as notificações PENDENTE.
CREATE TABLE notificacao (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chamado_id   INTEGER NOT NULL REFERENCES chamado (id),
    destinatario TEXT NOT NULL,
    assunto      TEXT NOT NULL DEFAULT '',
    mensagem     TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL
        CHECK (status IN ('PENDENTE', 'ENVIADA', 'FALHOU')),
    tentativas   INTEGER NOT NULL DEFAULT 0,
    -- Enquanto a reserva está vigente, as outras instâncias pulam esta notificação.
    -- NULL indica que ela está livre. Se a instância parar, a notificação
    -- fica disponível novamente quando a reserva expira.
    reservada_ate TIMESTAMPTZ
);

CREATE INDEX notificacao_pendente ON notificacao (id) WHERE status = 'PENDENTE';
