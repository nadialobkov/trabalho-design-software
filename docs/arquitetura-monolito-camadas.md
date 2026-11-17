# Arquitetura do Sistema de Manutenção de Equipamentos de Laboratório

## 1. Contexto

A manutenção dos equipamentos de laboratório envolve solicitantes, técnicos e coordenadores de diferentes departamentos da universidade. Sem um registro centralizado, a comunicação sobre problemas fica dispersa, o acompanhamento dos atendimentos se torna difícil e informações sobre soluções anteriores podem ser perdidas.

O sistema organiza esse processo por meio de chamados associados a equipamentos existentes. Solicitantes registram problemas e acompanham seus pedidos; coordenadores consultam demandas, classificam prioridades, atribuem técnicos e encaminham chamados; técnicos iniciam o atendimento, registram diagnóstico e intervenção e concluem a manutenção.

Além das funcionalidades, três requisitos orientam a organização da solução:

- **Rastreabilidade:** preservar o responsável, o momento e os dados de cada alteração relevante, permitindo reconstruir o histórico do atendimento.
- **Controle de acesso:** verificar permissões conforme o papel do usuário, seu departamento e sua relação com o chamado.
- **Confiabilidade das notificações:** preservar a abertura ou conclusão do chamado mesmo quando o serviço de e-mail estiver indisponível.

A arquitetura deve tornar essas responsabilidades explícitas e permitir a substituição de tecnologias de persistência e comunicação sem espalhar alterações pelas regras de negócio.

## 2. Arquitetura proposta e justificativas

A solução adota **monólito + cliente-servidor + organização em quatro camadas: apresentação, aplicação, domínio e infraestrutura**.

### 2.1. Monólito

O backend reúne as funcionalidades em uma única aplicação Python, implantada como uma unidade. Os componentes colaboram por chamadas internas e utilizam um banco de dados compartilhado.

Essa escolha mantém simples a execução e a configuração do sistema e permite utilizar transações locais. Uma operação como concluir um chamado precisa salvar a alteração do atendimento, o registro de auditoria e a notificação pendente de forma conjunta. A aplicação única e o banco compartilhado facilitam essa garantia: a gravação é confirmada integralmente ou revertida em caso de falha.

A organização monolítica é adequada ao escopo do trabalho porque permite concentrar o esforço nas regras, responsabilidades e consistência dos dados. A separação interna em camadas mantém o código organizado sem exigir comunicação remota entre suas partes.

PostgreSQL e o servidor de e-mail são dependências externas. Sua execução em processos ou contêineres separados não muda a classificação do backend, que continua sendo uma aplicação monolítica.

### 2.2. Cliente-servidor

Os usuários acessam um cliente web, responsável por apresentar informações e enviar solicitações HTTP com dados em JSON. O servidor recebe essas solicitações, verifica permissões, executa os casos de uso e acessa a persistência.

A centralização permite compartilhar os dados entre laboratórios e departamentos. Todos os clientes consultam o mesmo conjunto de chamados, evitando históricos isolados em computadores diferentes.

O servidor também concentra a autorização. A permissão para consultar, atribuir ou concluir um chamado deve ser verificada mesmo quando a operação é solicitada diretamente pela API. Os controles da interface ajudam o usuário, mas não substituem essa verificação.

A API permite acrescentar outras interfaces, como um aplicativo mobile, reutilizando os serviços de aplicação e as regras do domínio. A comunicação é implementada com FastAPI, e as telas web utilizam React.

### 2.3. Organização em camadas

As quatro camadas separam responsabilidades que possuem motivos diferentes para mudar:

| Camada | Responsabilidade principal | Justificativa |
|---|---|---|
| **Apresentação** | Receber solicitações, validar sua estrutura e apresentar resultados | Alterações em rotas, parâmetros e formato das respostas ficam separadas das regras de manutenção |
| **Aplicação** | Coordenar casos de uso e verificar permissões | A sequência de cada operação fica centralizada e pode ser acionada por diferentes interfaces |
| **Domínio** | Representar os conceitos e validar as regras do atendimento | As regras permanecem próximas das informações necessárias e independentes de tecnologias externas |
| **Infraestrutura** | Persistir dados e realizar comunicação externa | SQL e SMTP ficam concentrados nos componentes que conhecem essas tecnologias |

As camadas são divisões lógicas dentro da mesma aplicação. A comunicação entre elas ocorre por chamadas de métodos.

A apresentação utiliza os serviços de aplicação. A aplicação utiliza entidades do domínio e interfaces de persistência e notificação. A infraestrutura implementa essas interfaces e conhece as entidades que precisa armazenar ou recuperar. O domínio não depende de HTTP, SQL ou SMTP.

A escolha das implementações concretas ocorre no ponto de inicialização, `main.py`, que conecta os componentes por seus construtores. Essa organização permite utilizar PostgreSQL ou memória e envio SMTP ou simulado sem alterar o fluxo principal dos casos de uso.

### 2.4. Persistência e consistência

O PostgreSQL armazena equipamentos, usuários, departamentos, chamados, associações de técnicos, auditoria e notificações. A natureza relacional desses dados e a necessidade de transações justificam sua utilização.

O acesso utiliza SQL com `psycopg`, concentrado em `PostgresManutencaoRepositorio`. O serviço de aplicação utiliza o contrato `ManutencaoRepositorio`, sem conhecer consultas ou conexões.

A operação `salvar_chamado(chamado, auditoria, notificacao)` grava o chamado, suas associações, a auditoria e a notificação opcional na mesma transação. Isso evita confirmar uma alteração sem os registros necessários à rastreabilidade e ao processamento posterior da comunicação.

Chaves estrangeiras e restrições de integridade complementam as validações do domínio. Os registros de auditoria são protegidos contra atualizações e exclusões comuns, preservando as informações produzidas pelas operações.

O Docker Compose organiza a execução da aplicação, do banco e do Mailpit, utilizado como servidor de e-mail de demonstração. Um volume persistente mantém os dados entre reinícios.

### 2.5. Notificações e autorização

O envio de e-mail é separado da operação que modifica o chamado. A aplicação salva a notificação como pendente, e `AgendadorNotificacoes` aciona seu processamento a cada dez segundos. O serviço consulta as pendências, solicita o envio por `Notificador` e registra o resultado.

Essa separação impede que a indisponibilidade do e-mail desfaça uma abertura ou conclusão já registrada. As pendências persistidas podem ser retomadas após reinício da aplicação.

A política de envio prevê até cinco tentativas. Antes desse limite, uma falha mantém a notificação pendente; ao atingi-lo, ela passa para `FALHOU` e deixa de ser reenviada automaticamente. Essa política preserva o registro da falha, mas limita a recuperação automática a indisponibilidades superadas antes do esgotamento das tentativas.

A autorização é verificada no serviço de aplicação com base no usuário identificado, seu papel, departamento e relação com o chamado. O solicitante consulta seus próprios chamados; técnicos e coordenadores consultam os chamados de seu departamento. Operações de atendimento exigem as permissões correspondentes, como a atribuição do técnico responsável pela conclusão. Identificar um usuário e verificar sua autorização são responsabilidades distintas da comprovação de sua identidade por autenticação.

## 3. Modelo de domínio e responsabilidades

O modelo de domínio é orientado a objetos e possui seis entidades principais. `Chamado` ocupa a posição central, pois representa a solicitação e reúne as informações necessárias ao acompanhamento do atendimento.

| Entidade | Informações e responsabilidades |
|---|---|
| **Chamado** | Equipamento, solicitante, técnicos, departamento responsável, descrição do problema, informações adicionais, datas, prioridade e estado. Mantém diagnóstico, descrição da intervenção e responsável pela conclusão e valida as operações do ciclo de vida |
| **Equipamento** | Identificação, nome, laboratório e departamento. Fornece a referência necessária para associar chamados e consultar seu histórico |
| **Usuario** | Identificação, nome, e-mail, papel e departamento opcional. Informa se possui função de técnico ou de coordenador de determinado departamento |
| **Departamento** | Identificação e nome da unidade responsável pelos atendimentos |
| **RegistroAuditoria** | Chamado, autor, data e hora, campo alterado, valores anterior e novo e observação. Representa as alterações relevantes do atendimento |
| **Notificacao** | Chamado, destinatário, assunto, mensagem, estado e tentativas. Controla o resultado do envio e o limite de falhas |

### 3.1. Relacionamentos

Um equipamento pode estar associado a vários chamados, enquanto cada chamado se refere a um equipamento e a um solicitante. O chamado possui um departamento responsável e uma lista de técnicos, que pode estar vazia antes da atribuição.

Na abertura, o departamento responsável é obtido do equipamento. O encaminhamento altera essa responsabilidade e deve produzir auditoria com a justificativa da transferência.

Cada usuário possui um papel e um departamento opcional. As verificações utilizam essas informações diretamente. O diagnóstico e a descrição da intervenção são atributos do chamado, juntamente com o técnico que concluiu e a data de conclusão.

Um chamado pode possuir vários registros de auditoria e notificações. A auditoria preserva as mudanças relevantes nos dados e nas associações de técnicos. O modelo não mantém atividades técnicas como uma coleção de intervenções independentes: a descrição da solução pertence ao chamado, e suas alterações relevantes devem ser registradas na auditoria.

### 3.2. Regras do ciclo de vida

O fluxo principal do atendimento é:

```text
Aberto → Atribuído → Em atendimento → Concluído
```

As operações são atribuídas à entidade `Chamado`:

- `abrir()` valida a descrição, define o estado inicial e associa os dados do atendimento;
- `definir_prioridade()` estabelece a classificação entre baixa, média, alta e crítica;
- `atribuir_tecnico()` verifica a função do usuário e registra sua associação ao chamado;
- `iniciar_atendimento()` valida a passagem de atribuído para em atendimento;
- `concluir()` exige o estado em atendimento, diagnóstico e descrição da intervenção, registrando a conclusão e seu responsável;
- `encaminhar()` altera o departamento responsável.

O serviço de aplicação verifica a autorização antes de solicitar essas operações. A entidade preserva as regras que não podem ser violadas durante sua execução. Assim, uma pessoa autorizada ainda não pode concluir um chamado em estado inválido ou sem os dados obrigatórios.

## 4. Distribuição de responsabilidades

### 4.1. Apresentação

`TelaAbrirChamado` e `TelaListaChamados` apresentam os dados e enviam solicitações ao servidor. `ManutencaoController` recebe essas operações, utiliza esquemas para organizar entrada e saída e encaminha o processamento ao serviço.

O controller converte resultados e erros em respostas HTTP. Ele não realiza consultas SQL nem executa as regras de conclusão do atendimento.

`AgendadorNotificacoes` também pertence à apresentação do servidor, pois aciona um caso de uso por um evento de tempo. Sua responsabilidade é iniciar o processamento periódico; o envio efetivo pertence ao notificador.

### 4.2. Aplicação

`ManutencaoService` coordena os nove casos de uso:

| Caso de uso | Método |
|---|---|
| Registrar chamado | `abrir_chamado()` |
| Consultar chamados e aplicar filtros | `consultar_chamados()` |
| Definir prioridade | `definir_prioridade()` |
| Atribuir técnico | `atribuir_tecnico()` |
| Iniciar atendimento | `iniciar_atendimento()` |
| Concluir chamado | `concluir_chamado()` |
| Consultar histórico do equipamento | `consultar_historico()` |
| Encaminhar chamado | `encaminhar_chamado()` |
| Processar notificações pendentes | `reenviar_notificacoes()` |

O serviço verifica permissões, recupera informações, chama o domínio, prepara auditoria e notificações e solicita a persistência. `FiltrosChamado` reúne os critérios de consulta. O serviço também compõe a confirmação de abertura por meio de `preencher_confirmacao()`.

Na conclusão, por exemplo, a aplicação recupera o usuário e o chamado, verifica a atribuição e o departamento, solicita `Chamado.concluir()`, cria a auditoria e a notificação e chama o repositório. O serviço coordena a operação; a entidade valida as regras do atendimento; o repositório garante a gravação transacional.

### 4.3. Contratos e infraestrutura

| Contrato | Responsabilidade | Implementações |
|---|---|---|
| **ManutencaoRepositorio** | Consultar chamados, equipamentos, usuários, departamentos, histórico e auditoria; salvar alterações; consultar e atualizar notificações | `PostgresManutencaoRepositorio` e `RepositorioEmMemoria` |
| **Notificador** | Enviar uma notificação e comunicar falhas de envio | `SmtpNotificador` e `NotificadorFake` |

As interfaces ficam na aplicação porque representam suas necessidades. A infraestrutura fornece as implementações. O serviço recebe os objetos por seus construtores, sem decidir qual banco ou mecanismo de envio será utilizado.

O repositório PostgreSQL concentra SQL, conversão de dados e transações. O repositório em memória permite testar operações sem banco. O notificador SMTP conhece o protocolo de envio; o fake permite simular seu comportamento nos testes.

A operação de salvamento reúne os dados que precisam ser confirmados conjuntamente. O serviço não abre uma conexão SQL nem mantém a transação do chamado aberta durante o envio de e-mail.

## 5. Aplicação dos princípios GRASP

### 5.1. Information Expert — Especialista na informação

A responsabilidade deve ficar com o objeto que possui as informações necessárias para executá-la. `Chamado` conhece seu estado, técnicos, diagnóstico e descrição da intervenção, sendo responsável por validar seu ciclo de vida.

`Usuario` conhece seu papel e departamento e oferece verificações como `e_tecnico()` e `e_coordenador_de()`. `Notificacao` conhece seu estado e número de tentativas e controla as mudanças produzidas por sucesso ou falha de envio.

### 5.2. Controller — Controlador

`ManutencaoController` recebe solicitações externas e as encaminha ao `ManutencaoService`. O serviço atua como coordenador dos casos de uso, organizando autorização, recuperação de dados, execução das regras e persistência.

Essa distribuição evita que a interface execute o processo inteiro e permite que o agendador também utilize a camada de aplicação.

### 5.3. Low Coupling — Baixo acoplamento

O domínio não conhece banco de dados, HTTP ou serviço de e-mail. A aplicação utiliza `ManutencaoRepositorio` e `Notificador`, mantendo as dependências tecnológicas nas implementações de infraestrutura.

Assim, uma mudança no mecanismo de persistência ou envio pode ser concentrada na implementação do contrato, desde que suas garantias sejam preservadas. Por exemplo, substituir o acesso ao PostgreSQL não exige alterar a regra que impede concluir um chamado sem diagnóstico e intervenção.

As interfaces reduzem o acoplamento às tecnologias, mas não eliminam as dependências. O serviço continua dependendo das operações e garantias de `ManutencaoRepositorio`, de `Notificador` e das entidades do domínio. Alterar esses contratos ou o significado dos dados pode exigir mudanças no serviço. O objetivo é manter dependências explícitas e relacionadas ao negócio, evitando que detalhes de SQL e SMTP se propaguem pelos casos de uso.

### 5.4. High Cohesion — Alta coesão

As responsabilidades são agrupadas por propósito: controller trata comunicação, serviço coordena operações, entidades mantêm regras e dados do negócio, repositório persiste e notificador envia mensagens.

Os casos de uso foram reunidos em `ManutencaoService` porque pertencem ao mesmo processo de atendimento e compartilham informações e dependências de persistência e notificação. Para o escopo do trabalho, essa organização mantém a coordenação concentrada em um componente, sem introduzir serviços adicionais para cada operação.

Essa proximidade não torna todas as responsabilidades igualmente coesas. A composição de mensagens e o processamento de notificações possuem motivos de alteração diferentes daqueles da abertura, atribuição e conclusão dos chamados. Sua presença no mesmo serviço reduz a coesão e é uma simplificação consciente. Os detalhes de SQL e SMTP ficam fora dele, e as regras do ciclo de vida permanecem em `Chamado`, limitando a concentração de responsabilidades.

Se o conteúdo das mensagens ou as políticas de processamento passarem a evoluir de forma independente e frequente, essa será uma indicação concreta para separar tais responsabilidades. A avaliação da coesão considera a relação entre as tarefas e seus motivos de mudança, não apenas o número de métodos da classe.

### 5.5. Polymorphism, Indirection e Protected Variations

As implementações de repositório e notificador são utilizadas por suas interfaces. O polimorfismo permite trocar PostgreSQL por memória ou SMTP por uma simulação sem alterar a forma como o serviço chama essas dependências.

As interfaces oferecem uma indireção entre o caso de uso e a tecnologia, protegendo os consumidores das variações internas das implementações.

## 6. Aplicação dos princípios SOLID

### 6.1. SRP — Princípio da responsabilidade única

As responsabilidades são distribuídas entre comunicação, coordenação, regras de negócio, persistência e envio. Uma alteração em SQL pertence ao repositório, enquanto uma alteração na regra de conclusão pertence ao domínio.

O serviço concentra a coordenação dos casos de uso e a composição da confirmação. Uma mudança no texto do e-mail pode exigir sua alteração mesmo sem modificar o atendimento; uma mudança na política de autorização também pode afetá-lo sem alterar as mensagens. Esses são motivos distintos de mudança, portanto a aplicação de SRP nessa classe é parcial.

Essa concentração é aceita para manter simples a coordenação no escopo do trabalho, conforme a análise de coesão. A separação entre entidade, serviço, repositório e notificador impede que essa simplificação também incorpore ao serviço as regras do ciclo de vida e os mecanismos de banco e comunicação. A existência de camadas, por si só, não garante responsabilidade única em todas as classes.

### 6.2. OCP — Princípio aberto/fechado

Os contratos permitem acrescentar implementações de persistência e notificação preservando os consumidores existentes. Uma nova implementação é conectada na inicialização da aplicação.

Essa possibilidade depende da compatibilidade do contrato. Se um novo canal exigir destinatários ou conteúdos diferentes, o modelo de notificação também poderá precisar de alteração. O princípio orienta a extensão dos pontos identificados de variação, sem exigir abstrações para todas as mudanças possíveis.

### 6.3. LSP — Princípio da substituição de Liskov

Implementações que atendem à mesma interface devem preservar o comportamento esperado pelos consumidores. PostgreSQL e memória precisam respeitar os resultados das consultas e as garantias de salvamento. Notificadores devem respeitar o contrato de envio e de comunicação de falhas.

Compartilhar métodos com os mesmos nomes não basta: erros, efeitos e condições de uso também precisam ser compatíveis. Testes dos contratos ajudam a verificar essa substituição.

### 6.4. ISP — Princípio da segregação de interfaces

A separação entre `Notificador` e `ManutencaoRepositorio` distingue comunicação e persistência. `Notificador` possui uma operação específica de envio.

`ManutencaoRepositorio` é mais abrangente e reúne operações de diferentes entidades utilizadas pelo serviço. A escolha mantém um único contrato de persistência para coordenar o atendimento e explicita a gravação conjunta de chamado, auditoria e notificação. É uma organização simples para o consumidor principal, `ManutencaoService`.

Entretanto, o processamento de notificações precisa apenas de parte dessas operações e recebe acesso a um contrato mais amplo. Portanto, a segregação ocorre por tipo de dependência, sem uma divisão fina por consumidor. A escolha não representa atendimento integral ao ISP.

Se surgirem consumidores com necessidades independentes, contratos menores de consulta ou processamento de notificações poderão evitar dependências desnecessárias. Essa divisão não precisa eliminar a gravação atômica: interfaces diferentes podem compartilhar a mesma implementação e o mesmo mecanismo transacional. Assim, a abrangência atual é justificada pela simplicidade da coordenação, e não por uma exigência técnica do banco.

### 6.5. DIP — Princípio da inversão de dependências

`ManutencaoService` depende das interfaces `ManutencaoRepositorio` e `Notificador`, e não das classes concretas de PostgreSQL ou SMTP. A infraestrutura implementa essas interfaces, e o ponto de inicialização fornece os objetos ao serviço.

Essa direção de dependência mantém a coordenação do negócio independente dos mecanismos técnicos e permite testar os casos de uso com implementações simuladas. O domínio permanece livre das dependências de apresentação e infraestrutura.
