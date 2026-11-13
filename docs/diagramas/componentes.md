# Diagrama de componentes

Arquitetura: **cliente-servidor + monólito + camadas**, com interfaces nas bordas (estilo hexagonal).

Blocos com **borda grossa e ★** são implementados no protótipo (UC01 registrar chamado, UC02 consultar chamados e UC09 reenviar notificações). Os outros existem só no projeto.

## Como ler

Leia **de cima para baixo**:

1. O **navegador** mostra as telas React e chama o servidor por HTTP/JSON.
2. O **servidor** é um único programa Python (o monólito), dividido em quatro camadas:
   - **Apresentação** recebe o pedido (HTTP ou relógio);
   - **Aplicação** coordena os casos de uso;
   - **Domínio** guarda os dados e as regras;
   - **Infraestrutura** fala com o banco e com o e-mail.
3. As setas tracejadas **sobem** da Infraestrutura até as interfaces: a Infraestrutura **implementa** os contratos que a Aplicação define.
4. O banco e o servidor de e-mail ficam **fora** do servidor.

```mermaid
---
config:
  theme: neutral
  flowchart:
    rankSpacing: 45
    nodeSpacing: 30
    wrappingWidth: 320
    subGraphTitleMargin:
      top: 4
      bottom: 8
---
flowchart TB
    subgraph NAV["Navegador (cliente)"]
        UI["★ Telas React<br/>Abrir chamado · Lista de chamados"]
    end

    subgraph SRV["Servidor: monólito"]
        subgraph APRES["Apresentação"]
            CTRL["★ ManutencaoController<br/>rotas HTTP"]
            AGE["★ AgendadorNotificacoes<br/>envia e-mails pendentes a cada 10 s"]
        end
        subgraph APP["Aplicação"]
            MS["★ ManutencaoService<br/>9 casos de uso + verificar permissão"]
            IREPO["★ «interface»<br/>ManutencaoRepositorio"]
            INOT["★ «interface»<br/>Notificador"]
        end
        subgraph DOM["Domínio"]
            DOMN["★ Entidades<br/>Chamado · Equipamento<br/>Usuario · Departamento<br/>Notificacao · RegistroAuditoria"]
        end
        subgraph INFRA["Infraestrutura"]
            PG["★ PostgresManutencaoRepositorio"]
            MEM["★ RepositorioEmMemoria<br/>(testes, sem banco)"]
            SMTPN["★ SmtpNotificador"]
            FAKE["★ NotificadorFake<br/>(testes)"]
        end
    end

    DB[("PostgreSQL<br/>1 banco")]
    EMAIL{{"Servidor de e-mail<br/>Mailpit / Gmail"}}

    UI -->|"HTTP/JSON"| CTRL
    CTRL --> MS
    AGE --> MS
    MS --> IREPO
    MS --> INOT
    MS --> DOMN

    %% Links invisíveis: só posicionam o Domínio e a Infraestrutura na linha de baixo
    IREPO ~~~ DOMN
    IREPO ~~~ PG
    IREPO ~~~ MEM
    INOT ~~~ SMTPN
    INOT ~~~ FAKE

    PG -.->|implementa| IREPO
    MEM -.->|implementa| IREPO
    SMTPN -.->|implementa| INOT
    FAKE -.->|implementa| INOT

    PG -->|SQL| DB
    SMTPN -->|SMTP| EMAIL

    classDef impl stroke-width:3px
    class UI,CTRL,AGE,MS,IREPO,INOT,DOMN,PG,MEM,SMTPN,FAKE impl
```

## Legenda

- **Seta contínua (`-->`)**: "usa / chama".
- **Seta tracejada (`-.->`) com "implementa"**: a Infraestrutura implementa a interface. Nenhuma camada de cima conhece a Infraestrutura.
- **A Infraestrutura também conhece o Domínio** (para salvar e montar os objetos). Essa seta foi omitida para o desenho ficar limpo.
- **Links invisíveis (`~~~`)** no código só posicionam os blocos. Eles não são dependências.

## O que cada camada faz

| Camada | Faz | Não faz |
|---|---|---|
| Apresentação (navegador) | Telas React: mostram dados e enviam pedidos | Regras de negócio ou segurança |
| Apresentação (servidor) | Recebe o pedido (HTTP ou relógio), chama o service, converte erros em códigos HTTP | Decidir regras |
| Aplicação | O `ManutencaoService` coordena os passos de cada caso de uso: verifica permissão, busca, chama o domínio, salva, notifica | Conhecer SQL ou SMTP |
| Domínio | Guarda dados e regras do negócio | Falar com banco, e-mail ou HTTP |
| Infraestrutura | Fala com a tecnologia (SQL, SMTP) | Regras de negócio |
