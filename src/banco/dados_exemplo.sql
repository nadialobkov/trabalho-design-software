-- Usa os mesmos usuários e equipamentos de RepositorioEmMemoria.com_dados_de_exemplo().
-- Este script cadastra usuários e equipamentos porque o protótipo ainda não tem tela de cadastro.

INSERT INTO departamento (id, nome) VALUES
    (1, 'Elétrica'),
    (2, 'Óptica'),
    (3, 'Informática'),
    (4, 'Mecânica');

INSERT INTO usuario (id, nome, email, papel, departamento_id) VALUES
    (1, 'Ana',   'ana@example.com',   'SOLICITANTE', NULL),
    (2, 'Bruno', 'bruno@example.com', 'TECNICO',     1),
    (3, 'Carla', 'carla@example.com', 'COORDENADOR', 1),
    (4, 'Davi',  'davi@example.com',  'TECNICO',     2),
    (5, 'Eva',   'eva@example.com',   'SOLICITANTE', NULL),
    (6, 'Fábio', 'fabio@example.com', 'TECNICO',     1),
    (7, 'Helena','helena@example.com','COORDENADOR', 2),
    (8, 'Igor',  'igor@example.com',  'TECNICO',     3),
    (9, 'Juliana','juliana@example.com','COORDENADOR',3),
    (10,'Lucas', 'lucas@example.com','TECNICO',     4),
    (11,'Marina','marina@example.com','COORDENADOR',4),
    (12,'Paulo', 'paulo@example.com','SOLICITANTE',NULL);

INSERT INTO equipamento (id, nome, laboratorio, departamento_id) VALUES
    (10, 'Osciloscópio',     'Laboratório de Física',   1),
    (11, 'Fonte de bancada', 'Laboratório de Física',   1),
    (12, 'Microscópio',      'Laboratório de Biologia', 2),
    (13, 'Projetor',         'Sala Multimídia',         3),
    (14, 'Computador Lenovo','Laboratório de Redes',     3),
    (15, 'Servidor Dell',    'Centro de Dados',          3),
    (16, 'Centrífuga',       'Laboratório de Química',   4),
    (17, 'Balança analítica','Laboratório de Química',   4),
    (18, 'Espectrofotômetro','Laboratório de Química',   2),
    (19, 'Impressora 3D',    'Laboratório Maker',        4),
    (20, 'Bancada elétrica', 'Laboratório de Eletrônica',1),
    (21, 'Gerador de sinais','Laboratório de Telecomunicações',1);

INSERT INTO chamado
    (equipamento_id, solicitante_id, departamento_id, descricao_problema,
     informacoes_adicionais, data_ocorrencia, data_abertura, estado, prioridade)
VALUES
    (10, 1, 1, 'Osciloscópio apresenta ruído na tela', 'Chamado fictício para demonstração.', '2026-11-20', '2026-11-22 09:10:00', 'ATRIBUIDO', 'ALTA'),
    (13, 5, 3, 'Projetor não liga durante a aula', 'Chamado fictício para demonstração.', '2026-11-21', '2026-11-22 09:20:00', 'ABERTO', 'MEDIA'),
    (12, 1, 2, 'A lente não fica estabilizada', 'Chamado fictício para demonstração.', '2026-11-18', '2026-11-22 09:30:00', 'EM_ATENDIMENTO', 'URGENTE'),
    (14, 12, 3, 'Computador reinicia sozinho', 'Chamado fictício para demonstração.', '2026-11-17', '2026-11-22 09:40:00', 'CONCLUIDO', 'BAIXA'),
    (16, 5, 4, 'Centrífuga vibra excessivamente', 'Chamado fictício para demonstração.', '2026-11-16', '2026-11-22 09:50:00', 'ABERTO', 'ALTA'),
    (20, 12, 1, 'Bancada apresenta queda de tensão', 'Chamado fictício para demonstração.', '2026-11-15', '2026-11-22 10:00:00', 'ATRIBUIDO', 'URGENTE');

INSERT INTO chamado_tecnico (chamado_id, tecnico_id) VALUES
    (1, 2),
    (3, 4),
    (4, 8),
    (6, 6);
