# Diagramas de sequência

## 1. Caso de uso: concluir chamado

O caso de uso **UC06 — Concluir chamado** representa a solicitação de um técnico para encerrar um atendimento, informando diagnóstico e descrição da intervenção realizada. O fluxo descreve o comportamento projetado para o RF07 e prepara a comunicação de conclusão prevista no RF08. As operações UC06 marcadas como planejadas no diagrama de classes são representadas aqui como parte do projeto do sistema.

A sequência apresenta a colaboração entre apresentação, aplicação, domínio e infraestrutura em uma aplicação monolítica. As chamadas internas são chamadas de métodos; HTTP é utilizado entre cliente e servidor, SQL na persistência e SMTP no envio externo.

A conclusão permite demonstrar os três ASRs: autorização do técnico, registro de auditoria e persistência da notificação para envio posterior.

### Participantes e responsabilidades

| Participante | Camada | Responsabilidade |
|---|---|---|
| Técnico | Ator externo | Solicitar a conclusão e fornecer diagnóstico e intervenção |
| `ManutencaoController` | Apresentação | Receber a solicitação e devolver o resultado HTTP |
| `ManutencaoService` | Aplicação | Verificar permissão, coordenar a conclusão e preparar auditoria e notificação |
| `Usuario` | Domínio | Fornecer papel e departamento para as verificações |
| `Chamado` | Domínio | Validar o estado e os dados obrigatórios e registrar a conclusão |
| `RegistroAuditoria` | Domínio | Representar autor, instante e alteração realizada |
| `Notificacao` | Domínio | Representar a comunicação pendente ao solicitante |
| `PostgresManutencaoRepositorio` | Infraestrutura | Implementar `ManutencaoRepositorio` e salvar os registros em uma transação |
| PostgreSQL | Serviço externo | Armazenar os dados e confirmar ou reverter a transação |

O ator representa a interação do técnico pela interface cliente. Não é introduzida uma classe de tela de conclusão. O participante `repo:ManutencaoRepositorio` representa um objeto `PostgresManutencaoRepositorio` utilizado pelo contrato da aplicação. Assim, a sequência mostra quem executa a persistência sem estabelecer uma dependência do serviço com a classe concreta.

Os argumentos das mensagens explicam os dados necessários à colaboração; a notação não pretende fixar todas as assinaturas dos métodos. `verificar_permissao()` é uma operação interna do serviço. A autorização da conclusão considera o papel do usuário, seu departamento e sua presença entre os técnicos do chamado.

### Sequência principal e fluxos alternativos

```mermaid
sequenceDiagram
    autonumber
    actor T as Técnico
    box Apresentação
        participant C as ManutencaoController
    end
    box Aplicação
        participant S as ManutencaoService
    end
    box Domínio
        participant U as usuario:Usuario
        participant CH as chamado:Chamado
        participant AU as auditoria:RegistroAuditoria
        participant N as notificacao:Notificacao
    end
    box Infraestrutura
        participant R as repo:ManutencaoRepositorio
    end
    participant DB as PostgreSQL

    T->>C: Solicitar conclusão via HTTP<br/>(chamado_id, diagnóstico, intervenção)
    Note over T,C: A requisição também identifica o usuário
    C->>S: concluir_chamado(usuario_id, chamado_id,<br/>diagnostico, descricao_intervencao)
    S->>S: verificar_permissao(usuario_id, ação de conclusão)
    S->>R: buscar_usuario(usuario_id)
    R->>DB: Consultar usuário
    DB-->>R: Dados do usuário ou ausência
    R-->>S: usuario ou ausência

    break Usuário ausente ou desconhecido
        S-->>C: AcessoNegado
        C-->>T: HTTP 403
    end

    S->>R: buscar_chamado(chamado_id)
    R->>DB: Consultar chamado e associações
    DB-->>R: Dados do chamado ou ausência
    R-->>S: chamado ou ausência

    break Chamado inexistente
        S-->>C: Resultado de recurso inexistente
        C-->>T: HTTP 404
    end

    S->>U: e_tecnico()
    U-->>S: Resultado
    Note over S,CH: Serviço verifica papel, departamento<br/>e presença do usuário em chamado.tecnicos

    break Usuário não autorizado para esse chamado
        S-->>C: AcessoNegado
        C-->>T: HTTP 403
    end

    Note over S,CH: Serviço guarda estado anterior e instante da operação
    S->>CH: concluir(diagnóstico, intervenção,<br/>técnico e instante)

    alt Estado diferente de EM_ATENDIMENTO ou dados obrigatórios vazios
        CH-->>S: ValueError
        S-->>C: Erro de validação do domínio
        C-->>T: HTTP 422
    else Conclusão válida
        Note over CH: Atualiza estado para CONCLUIDO,<br/>diagnostico, descricao_intervencao,<br/>concluido_por e data_conclusao
        CH-->>S: Conclusão aplicada ao objeto
        S->>AU: Construir registro com autor, instante<br/>e estado anterior e novo
        Note over S,AU: Observação registra o contexto da conclusão,<br/>incluindo diagnóstico e intervenção
        S->>N: Construir notificação PENDENTE<br/>para o solicitante, com conteúdo da conclusão
        S->>R: salvar_chamado(chamado, auditoria, notificacao)
        R->>DB: BEGIN
        R->>DB: Gravar chamado, auditoria e notificação

        alt Falha durante a gravação
            DB-->>R: Erro de persistência
            R->>DB: ROLLBACK
            R-->>S: Falha de persistência
            S-->>C: Operação não confirmada
            C-->>T: HTTP 500
            Note over S,DB: Nenhuma alteração da operação é confirmada no banco<br/>O objeto alterado em memória não deve ser tratado como salvo
        else Gravação bem-sucedida
            DB-->>R: Registros gravados na transação
            R->>DB: COMMIT
            DB-->>R: Transação confirmada
            R-->>S: Salvamento concluído
            S-->>C: Resultado da conclusão
            C-->>T: HTTP 200 — chamado concluído
            Note over N,DB: Notificação persistida para processamento posterior
        end
    end
```

`BEGIN`, `COMMIT` e `ROLLBACK` explicitam a fronteira transacional da operação. Essa fronteira é executada pela infraestrutura, inclusive quando gerenciada pelo contexto de conexão da biblioteca de banco; o serviço não envia SQL diretamente.

O fluxo de chamado inexistente utiliza uma resposta 404 sem introduzir uma nova classe de exceção no modelo. A resposta 500 representa uma falha interna de persistência, sem exposição de detalhes do banco ao cliente.

O registro de auditoria identifica a mudança de estado e mantém o contexto da conclusão em `observacao`. Quando houver alteração posterior de campos, novos registros devem preservar os respectivos valores anteriores e novos. Diagnóstico e descrição da intervenção pertencem ao próprio `Chamado`; não há um participante separado chamado `Intervencao`.

## 2. Processamento posterior de notificações

O **UC09 — Reenviar notificações** é acionado pelo relógio e não pelo técnico. Ele ocorre separadamente da requisição de conclusão, podendo processar notificações tanto de abertura quanto de conclusão.

`AgendadorNotificacoes` inicia o processamento. `ManutencaoService` consulta pendências e coordena o envio. O participante `notificador:Notificador` representa uma instância de `SmtpNotificador`, utilizada pelo contrato da aplicação. A entidade `Notificacao` controla estado e tentativas.

```mermaid
sequenceDiagram
    autonumber
    box Apresentação
        participant A as AgendadorNotificacoes
    end
    box Aplicação
        participant S as ManutencaoService
    end
    box Domínio
        participant N as notificacao:Notificacao
    end
    box Infraestrutura
        participant R as repo:ManutencaoRepositorio
        participant E as notificador:Notificador
    end
    participant DB as PostgreSQL
    participant SMTP as Servidor de e-mail

    Note over A,SMTP: Processamento posterior à persistência da operação
    A->>A: executar() a cada 10 segundos
    A->>S: reenviar_notificacoes()
    S->>R: listar_pendentes()
    R->>DB: Selecionar e reservar notificações PENDENTE<br/>disponíveis para processamento
    DB-->>R: Registros selecionados
    R-->>S: Lista de notificações

    loop Para cada notificação retornada
        S->>E: enviar(notificacao)
        E->>SMTP: Enviar mensagem por SMTP

        alt Serviço aceita a mensagem
            SMTP-->>E: Aceitação
            E-->>S: Envio realizado
            S->>N: marcar_enviada()
            Note over N: status = ENVIADA
        else Serviço indisponível ou erro no envio
            SMTP-->>E: Falha ou ausência de resposta
            E-->>S: OSError
            S->>N: registrar_falha()
            Note over N: Incrementa tentativas
            alt Menos de 5 falhas
                Note over N: status = PENDENTE<br/>Disponível para uma tentativa posterior
            else Limite de 5 falhas atingido
                Note over N: status = FALHOU<br/>Sem nova tentativa automática
            end
        end

        S->>R: atualizar_notificacao(notificacao)
        R->>DB: Persistir status e tentativas<br/>e liberar a reserva
        DB-->>R: Atualização confirmada
        R-->>S: Atualização concluída
    end

    S-->>A: Rodada de processamento encerrada
```

A seleção utiliza reservas temporárias para reduzir o processamento simultâneo da mesma mensagem. Se o processamento for interrompido, a reserva expira após cinco minutos. Uma falha após o SMTP aceitar a mensagem e antes da gravação do sucesso pode causar reenvio; a reserva não garante entrega exatamente uma vez.

O estado `ENVIADA` indica que o envio foi aceito pelo serviço SMTP, não que o solicitante leu a mensagem. Se a persistência do resultado falhar, não é possível considerar o estado atualizado no banco; o tratamento do agendador deve permitir rodadas posteriores.

A política de cinco tentativas limita a recuperação automática. Uma mensagem em `FALHOU` permanece armazenada, mas não é selecionada por `listar_pendentes()`. Portanto, o fluxo não garante envio automático após indisponibilidades que esgotem esse limite.

## 3. Relação com requisitos e responsabilidades

| Etapa | Requisito ou princípio demonstrado |
|---|---|
| Verificação do papel, departamento e atribuição do técnico | ASR02 — controle de acesso |
| Validação do estado, diagnóstico e intervenção em `Chamado.concluir()` | RF07, RN03 e GRASP Information Expert |
| Coordenação da operação pelo serviço, sem SQL ou SMTP | GRASP Controller, baixo acoplamento e separação de responsabilidades |
| Persistência conjunta de chamado e auditoria | ASR01 — rastreabilidade e consistência |
| Registro da notificação junto à conclusão | RF08 e ASR03 — preservação da comunicação pendente |
| Envio posterior pelo serviço e notificador | Independência entre a conclusão e a disponibilidade do e-mail |
| Uso de `ManutencaoRepositorio` e `Notificador` | SOLID DIP e possibilidade de substituição das implementações |

Os dois diagramas se complementam: o primeiro termina com a confirmação do atendimento, enquanto o segundo trata a comunicação posterior. Essa divisão evidencia que o técnico não precisa aguardar o envio do e-mail para receber a confirmação da conclusão.
