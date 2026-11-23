-- Usa os mesmos usuários e equipamentos de RepositorioEmMemoria.com_dados_de_exemplo().
-- Este script cadastra usuários e equipamentos porque o protótipo ainda não tem tela de cadastro.

INSERT INTO departamento (id, nome) VALUES
    (1, 'Elétrica'),
    (2, 'Óptica');

INSERT INTO usuario (id, nome, email, papel, departamento_id) VALUES
    (1, 'Ana',   'ana@example.com',   'SOLICITANTE', NULL),
    (2, 'Bruno', 'bruno@example.com', 'TECNICO',     1),
    (3, 'Carla', 'carla@example.com', 'COORDENADOR', 1),
    (4, 'Davi',  'davi@example.com',  'TECNICO',     2),
    (5, 'Eva',   'eva@example.com',   'SOLICITANTE', NULL);

INSERT INTO equipamento (id, nome, laboratorio, departamento_id) VALUES
    (10, 'Osciloscópio',     'Laboratório de Física',   1),
    (11, 'Fonte de bancada', 'Laboratório de Física',   1),
    (12, 'Microscópio',      'Laboratório de Biologia', 2);
