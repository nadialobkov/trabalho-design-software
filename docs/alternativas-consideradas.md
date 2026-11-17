# Alternativas arquiteturais consideradas

## 1. Contexto da decisão

O Sistema de Manutenção de Equipamentos de Laboratório precisa compartilhar chamados entre solicitantes, técnicos e coordenadores de diferentes departamentos. As operações devem respeitar permissões, preservar o histórico e permitir o encaminhamento dos atendimentos sem perder os registros anteriores.

A solução escolhida é **monólito + cliente-servidor + organização em quatro camadas**, com persistência centralizada em PostgreSQL e envio posterior de notificações. Foram consideradas três alternativas: monólito modular, microsserviços e arquitetura orientada a eventos.

As alternativas representam diferentes decisões de organização e comunicação e não são mutuamente exclusivas. Um monólito modular pode possuir camadas e utilizar eventos, assim como microsserviços podem adotar comunicação orientada a eventos. A comparação explicita o que cada alternativa acrescentaria à solução escolhida: fronteiras por capacidades de negócio, distribuição em serviços ou colaboração predominantemente por eventos.

Os critérios são modificabilidade, desempenho, disponibilidade, testabilidade, complexidade, implantação, escalabilidade e custo de desenvolvimento e operação. Não foram realizados testes comparativos de desempenho; a análise considera as características estruturais de cada alternativa e as necessidades do projeto.

Os três ASRs orientam a decisão:

| ASR | Necessidade que influencia a arquitetura |
|---|---|
| **ASR01 — Rastreabilidade** | Preservar alterações de chamado, autoria e instante, mantendo consistência entre a operação e sua auditoria |
| **ASR02 — Controle de acesso** | Verificar papel, departamento e relação com o chamado em cada operação e consulta |
| **ASR03 — Confiabilidade das notificações** | Preservar o atendimento e registrar a comunicação pendente mesmo quando o serviço externo estiver indisponível |

## 2. Alternativa A — Monólito modular

### Organização

O backend continuaria sendo uma aplicação com implantação única, mas seria organizado por capacidades de negócio, como gestão de chamados, equipamentos, usuários/departamentos e notificações. Cada módulo teria responsabilidades, contratos públicos e limites de acesso aos seus dados e detalhes internos.

Cada módulo poderia manter suas próprias camadas. A diferença para a solução escolhida seria a existência de fronteiras de negócio explícitas, além da divisão técnica entre apresentação, aplicação, domínio e infraestrutura. Criar pastas por funcionalidade, isoladamente, não asseguraria esses limites.

### Benefícios

- Contratos internos e regras de dependência delimitariam o alcance das alterações.
- Capacidades de negócio poderiam ser testadas com maior isolamento.
- A implantação continuaria única, sem exigir chamadas de rede entre módulos.
- Fronteiras bem definidas poderiam facilitar a distribuição futura de responsabilidades entre equipes ou a avaliação de uma extração para serviço independente.

### Relação com os ASRs

| ASR | Avaliação |
|---|---|
| **ASR01** | Permite salvar chamado e auditoria em uma transação local. Se a operação atravessar módulos, seus contratos precisam definir como colaborar sem contornar os limites de acesso |
| **ASR02** | Permite centralizar políticas compartilhadas e verificar permissões nas operações de cada módulo. Os limites precisam evitar acessos internos que contornem a autorização |
| **ASR03** | Um módulo de notificações pode concentrar pendências e tentativas. A gravação conjunta do chamado e da notificação continua possível quando participam do mesmo mecanismo transacional |

### Motivos para descarte

No escopo do trabalho, os casos de uso estão concentrados em um processo de manutenção e utilizam um conjunto reduzido de entidades e integrações. As quatro camadas já permitem separar comunicação, coordenação, regras e mecanismos técnicos.

Acrescentar fronteiras de negócio exigiria definir a propriedade dos dados, os contratos de colaboração e verificações que impeçam acessos indevidos entre módulos. Esse esforço pode ser valioso em uma aplicação maior, mas não há, no escopo definido, necessidade suficiente de evolução independente dessas capacidades para justificar essa organização adicional.

A alternativa foi descartada pela relação entre esforço e benefício no projeto, não por incompatibilidade com os ASRs. Compartilhar dados ou realizar transações conjuntas não impede um monólito modular. A escolha pelas camadas também exige disciplina para evitar concentração excessiva de responsabilidades; a ausência de módulos não elimina esse cuidado.

### Quando seria adequada

Poderia ser reconsiderada se chamados, equipamentos, usuários ou notificações passassem a apresentar regras extensas, ritmos de alteração distintos ou responsáveis diferentes. Nesse cenário, fronteiras internas explícitas ajudariam a controlar dependências sem exigir distribuição em microsserviços.

## 3. Alternativa B — Microsserviços

### Organização

A solução seria dividida em serviços implantados de forma independente, por exemplo para atendimento de chamados, consulta de equipamentos, usuários/departamentos e notificações. A comunicação ocorreria por APIs ou mensagens, e cada serviço seria responsável pelos dados sob seu controle.

Os limites precisariam ser definidos segundo responsabilidades de negócio. Não bastaria transformar cada classe em um serviço. A divisão também exigiria estabelecer contratos de comunicação, comportamento diante de falhas e consistência entre os dados distribuídos.

### Benefícios

- Serviços com demandas diferentes poderiam receber recursos de execução separadamente.
- Uma equipe poderia alterar e implantar um serviço sem necessariamente implantar os demais, desde que preservasse os contratos.
- O processamento de notificações poderia executar de forma independente do atendimento HTTP.
- Algumas falhas poderiam ficar isoladas, desde que os serviços consumidores fossem preparados para a indisponibilidade das dependências.

### Relação com os ASRs

| ASR | Avaliação |
|---|---|
| **ASR01** | Se chamado e auditoria permanecerem no mesmo serviço e banco, uma transação local continua possível. Se forem separados, será necessário coordenar registros distribuídos, preservar causalidade e tratar falhas entre as etapas |
| **ASR02** | Cada serviço responsável por uma operação deve aplicar a autorização necessária. Identidade, informações departamentais e contratos de acesso precisam ser propagados e mantidos consistentes; uma verificação apenas na entrada não resolve todos os acessos internos |
| **ASR03** | Um serviço de notificações pode processar mensagens de forma independente. Para evitar perder a comunicação entre a confirmação do chamado e o envio da mensagem, são necessários mecanismos como registro transacional da pendência, publicação posterior, novas tentativas e tratamento de duplicação |

### Motivos para descarte

O escopo do trabalho não apresenta uma necessidade concreta de implantação independente ou escalabilidade distinta para cada parte do sistema. A equipe precisa demonstrar um processo de manutenção consistente, com regras, auditoria e notificações, sem acrescentar infraestrutura que não seja justificada pelos requisitos.

A distribuição introduziria falhas parciais: o serviço de chamados poderia confirmar uma operação enquanto o serviço de notificações estivesse indisponível, ou uma consulta de autorização poderia falhar por problemas de comunicação. Esses cenários são tratáveis, mas exigem protocolos, tratamento de repetição, identificação de mensagens e acompanhamento das interações entre processos.

Também seria necessário configurar e manter mais unidades de execução, contratos de API e testes de integração. Chamadas remotas acrescentariam latência e pontos de falha às operações que, em um monólito, podem ser realizadas por chamadas locais.

Microsserviços não impedem consistência ou auditoria, mas exigem mais mecanismos para preservá-las quando uma operação atravessa fronteiras de serviços. Como esses custos não são compensados por uma necessidade demonstrada de independência operacional, a alternativa foi descartada para o escopo atual.

### Quando seria adequada

Essa alternativa poderia ser reconsiderada caso houvesse equipes independentes, necessidade comprovada de escalar apenas determinadas funções, ciclos de implantação distintos ou requisitos de isolamento operacional que justificassem a distribuição. A decisão deveria partir dessas necessidades e da definição de limites de dados e transações.

## 4. Alternativa C — Arquitetura orientada a eventos

### Organização

A colaboração entre funcionalidades seria baseada predominantemente na publicação e no consumo de eventos que representam fatos já ocorridos, como `ChamadoAberto`, `PrioridadeAlterada` e `ChamadoConcluido`. Componentes interessados reagiriam a esses eventos para gerar notificações, atualizar consultas ou realizar integrações.

A solicitação de conclusão ainda seria autorizada e validada antes de produzir `ChamadoConcluido`. Publicar o evento não substituiria as regras que determinam se o técnico pode concluir o chamado.

Eventos podem ser processados dentro de um monólito ou entre processos. Para esta alternativa, considera-se publicação durável e processamento assíncrono por consumidores, com um mecanismo de distribuição e recuperação de mensagens. Um broker é uma opção de implementação, não uma exigência de toda arquitetura orientada a eventos. A alternativa também não pressupõe event sourcing: o estado atual pode continuar armazenado em tabelas relacionais.

### Benefícios

- Novas reações a um atendimento poderiam ser adicionadas como consumidores sem incluir todas elas no serviço que registra a operação.
- Produtores não precisariam conhecer cada implementação interessada no evento.
- Processamento assíncrono poderia absorver picos, desde que houvesse armazenamento durável e capacidade posterior de consumo.
- Integrações como notificações, relatórios e sistemas institucionais poderiam acompanhar os mesmos fatos de negócio.

### Relação com os ASRs

| ASR | Avaliação |
|---|---|
| **ASR01** | Eventos podem transportar autoria, instante e dados da alteração. Porém, a emissão de eventos não garante auditoria por si só: é preciso preservar os registros, sua relação com a operação e a ordem relevante por chamado |
| **ASR02** | A operação solicitada deve ser autorizada antes de alterar o estado e publicar seu evento. Consumidores também precisam controlar ações e dados expostos; identidade e contexto não devem ser aceitos sem critérios de confiança |
| **ASR03** | Eventos duráveis permitem consumo posterior e novas tentativas. Para evitar perda entre salvar o chamado e publicar o evento, pode-se registrar a pendência de publicação na mesma transação e distribuí-la depois; consumidores devem tratar repetição |

### Motivos para descarte

O sistema possui uma necessidade clara de processamento posterior para e-mails, mas não apresenta um conjunto amplo de consumidores independentes que justifique organizar a colaboração principal por eventos. Os casos de uso de atendimento podem ser coordenados diretamente pelo serviço, preservando transações locais e respostas imediatas sobre o resultado das operações.

Uma colaboração predominantemente assíncrona exigiria definir contratos e versões de eventos, políticas de repetição, tratamento de mensagens não processadas, identificação das operações e acompanhamento dos consumidores. Também seria necessário lidar com leituras temporariamente desatualizadas quando consultas fossem mantidas por consumidores e garantir que eventos repetidos não produzissem efeitos duplicados.

Esses mecanismos são justificáveis quando várias funcionalidades ou integrações precisam reagir de maneira independente. No escopo atual, a tabela de notificações pendentes e seu processador atendem à necessidade específica de separar o envio de e-mail da operação de manutenção, sem introduzir um fluxo geral de eventos de negócio.

Portanto, foi descartada a adoção de eventos como forma predominante de colaboração. Isso não exclui o processamento assíncrono já escolhido para notificações nem impede a introdução localizada de eventos se surgir uma necessidade concreta.

### Quando seria adequada

Seria especialmente útil se a universidade precisasse integrar o atendimento a estoque de peças, relatórios, indicadores, diferentes canais de comunicação ou outros sistemas que reagissem de maneira independente às mudanças dos chamados. A necessidade de consumidores autônomos e de processamento desacoplado justificaria avaliar essa evolução.

## 5. Comparação das alternativas

| Critério | Monólito em camadas — escolhido | A — Monólito modular | B — Microsserviços | C — Orientada a eventos |
|---|---|---|---|---|
| **Modificabilidade** | Camadas e interfaces isolam tecnologia e regras | Fronteiras de negócio limitam alterações entre capacidades | Serviços evoluem independentemente se preservarem contratos remotos | Novos consumidores ampliam reações; contratos de eventos precisam ser preservados |
| **Desempenho** | Chamadas internas locais e transações em um banco | Chamadas internas locais; modularidade não implica ganho automático de desempenho | Chamadas remotas acrescentam custo | Processamento assíncrono desloca trabalho, mas acrescenta espera e custo de distribuição |
| **Disponibilidade** | Depende do backend e do banco; envio de e-mail é posterior | Mesma unidade de execução, sem isolamento automático de falhas | Pode isolar falhas, conforme dependências e mecanismos de recuperação | Consumidores podem retomar pendências duráveis; armazenamento e distribuição também precisam estar disponíveis |
| **Testabilidade** | Testes de entidades e serviços com implementações simuladas | Permite verificar módulos e seus contratos internos | Requer testes de contratos e falhas distribuídas | Requer testar ordem relevante, duplicação, repetição e efeitos assíncronos |
| **Complexidade** | Coordenação direta e responsabilidades por camadas | Acrescenta limites de acesso e contratos por capacidade | Acrescenta coordenação entre processos e dados distribuídos | Acrescenta contratos de eventos, recuperação e acompanhamento de consumidores |
| **Implantação** | Backend implantado como uma unidade | Backend continua com implantação única | Várias unidades implantáveis | Pode manter implantação única ou separar consumidores; depende do desenho adotado |
| **Escalabilidade** | Aplicação dimensionada como conjunto | Em geral dimensionado como conjunto | Dimensionamento independente por serviço | Consumo pode ser ampliado se distribuído, respeitando ordem, concorrência e capacidade da fila |
| **Custo** | Compatível com o processo e a equipe do trabalho | Mais esforço de definição e manutenção das fronteiras | Mais infraestrutura, monitoramento e testes de integração | Mais mecanismos de entrega, evolução de contratos e investigação de fluxos assíncronos |

As alternativas não garantem atributos de qualidade apenas por sua classificação. Um monólito modular não oferece automaticamente implantação independente; microsserviços podem propagar falhas; eventos não garantem entrega ou auditoria sem persistência e recuperação adequadas. A comparação se refere às decisões descritas para cada opção, sem pressupor recursos não definidos no projeto.

## 6. Justificativa da solução escolhida

O **monólito cliente-servidor em quatro camadas** reúne os benefícios necessários ao problema: compartilhamento centralizado, aplicação uniforme das permissões e possibilidade de confirmar operações relacionadas em uma transação local.

Para o **ASR01**, chamado e auditoria são persistidos conjuntamente. A transação evita confirmar a alteração sem registrar seu histórico, enquanto a proteção dos registros de auditoria preserva a sequência das operações.

Para o **ASR02**, o servidor verifica o usuário, seu papel, departamento e relação com o chamado. Os diferentes clientes utilizam os mesmos casos de uso e políticas de autorização, sem depender apenas dos controles visuais da interface.

Para o **ASR03**, a notificação é registrada junto com o atendimento e enviada posteriormente. Essa separação permite confirmar o chamado mesmo quando o SMTP falha. Ela não depende da adoção de microsserviços: um processador dentro da aplicação pode consultar as pendências persistidas e executar as tentativas.

A organização em apresentação, aplicação, domínio e infraestrutura mantém regras, coordenação e tecnologia separadas. Interfaces de persistência e notificação permitem substituir mecanismos e utilizar implementações simuladas nos testes. Para o escopo definido, essa separação é suficiente sem acrescentar fronteiras por capacidades de negócio, serviços independentes ou uma colaboração predominantemente baseada em eventos.

### Consequências aceitas

As funcionalidades do backend são implantadas conjuntamente e compartilham recursos de execução. O acesso centralizado depende da disponibilidade da aplicação e do banco, e a equipe precisa preservar a separação de responsabilidades para evitar concentração excessiva no serviço de aplicação.

O processamento de notificações também depende de a aplicação estar em execução. Além disso, a política de cinco falhas interrompe as tentativas automáticas ao marcar a mensagem como `FALHOU`. A escolha arquitetural oferece uma base para recuperação persistente, mas essa política limita a recuperação automática após indisponibilidade prolongada; a arquitetura, isoladamente, não garante atendimento integral ao ASR03.

Essas consequências são assumidas de forma explícita. A decisão prioriza uma solução centralizada e consistente, com complexidade compatível com as necessidades e o escopo do trabalho.
