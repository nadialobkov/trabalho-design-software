# Trade-offs da arquitetura escolhida

## 1. Contexto e critérios

A solução adota **monólito + cliente-servidor + organização em quatro camadas**, com PostgreSQL, interfaces para persistência e notificação e envio de e-mails posterior à operação de atendimento.

Um trade-off é uma escolha que favorece determinados objetivos e impõe custos ou limitações a outros. A avaliação considera o compartilhamento entre departamentos, a rastreabilidade, o controle de acesso e a confiabilidade das notificações, além da complexidade compatível com o trabalho.

Os benefícios descritos dependem da implementação correta dos contratos, transações e verificações. Não foram realizados testes comparativos de desempenho ou disponibilidade; as consequências apresentadas são uma análise qualitativa da organização proposta.

| Decisão | Benefício priorizado | Custo ou limitação aceita |
|---|---|---|
| Backend monolítico | Implantação simples e chamadas internas locais | Implantação conjunta e compartilhamento de recursos e falhas |
| Cliente-servidor | Dados e autorização centralizados | Dependência de rede, backend e banco para o atendimento |
| Quatro camadas e interfaces | Separação de responsabilidades e substituição de tecnologias | Mais contratos, conversões e necessidade de disciplina |
| Serviço e repositório abrangentes | Coordenação simples do processo de manutenção | Menor segregação e concentração de motivos de alteração |
| PostgreSQL e transações locais | Consistência entre chamado, auditoria e notificação | Dependência do banco, contenção e evolução coordenada do esquema |
| SQL direto | Controle explícito das consultas e transações | Mapeamento e manutenção manuais |
| Auditoria preservada | Reconstrução do histórico | Crescimento dos dados e necessidade de registros completos |
| Notificações posteriores | Atendimento independente da disponibilidade do SMTP | Entrega não imediata e necessidade de recuperação |
| Processador dentro da aplicação | Menos serviços para operar | Processamento depende da aplicação e compartilha seus recursos |
| Limite de tentativas | Limita repetição automática de falhas | Pode impedir recuperação automática após indisponibilidade prolongada |

## 2. Monólito: simplicidade operacional e implantação conjunta

Uma única aplicação reúne os casos de uso. Isso reduz a quantidade de unidades a configurar, iniciar, observar e implantar. Chamadas entre controller, serviço e domínio ocorrem no mesmo processo, sem protocolos remotos entre essas partes.

A operação de concluir um chamado também pode salvar seus dados, a auditoria e a notificação em uma transação local. Essa característica favorece o ASR01 e o registro consistente da pendência necessária ao ASR03.

Em contrapartida, uma alteração em qualquer funcionalidade exige uma nova implantação do backend. As funcionalidades compartilham recursos, e um problema no processo pode afetar várias operações. A capacidade é ampliada para a aplicação como conjunto, sem dimensionamento independente de cada função.

**Justificativa da escolha:** o escopo não apresenta uma necessidade comprovada de equipes, ciclos de implantação ou cargas independentes. Manter uma aplicação permite concentrar o esforço nas regras e na consistência do atendimento.

**Como controlar o custo:** preservar as responsabilidades das camadas e acompanhar falhas e consumo de recursos. Uma futura replicação exige verificar concorrência e processamento de notificações; não deve ser tratada como simples multiplicação de processos sem coordenação.

## 3. Cliente-servidor: centralização e dependência de disponibilidade

O servidor oferece uma visão compartilhada dos chamados. Solicitantes, técnicos e coordenadores utilizam os mesmos dados, e a autorização é aplicada nos casos de uso, inclusive quando acessados diretamente pela API. Isso favorece o ASR02 e o encaminhamento de atendimentos entre departamentos.

O custo é que as operações dependem da comunicação com o servidor e da disponibilidade da aplicação e do banco. Uma interrupção nesses componentes pode impedir o acesso de todos os clientes. Também são necessárias validação de requisições e conversão de dados para HTTP/JSON.

**Justificativa da escolha:** a colaboração entre departamentos é central ao problema. Uma base compartilhada evita acrescentar sincronização entre instalações independentes e permite aplicar políticas uniformes de acesso.

**Como controlar o custo:** configurar persistência durável e procedimentos de recuperação, monitorar os serviços e manter a autorização no servidor. A arquitetura permite redundância futura, mas não implica alta disponibilidade automaticamente. A autorização também depende de uma identidade confiável; informar um identificador de usuário não substitui autenticação.

## 4. Camadas e interfaces: modificabilidade e esforço de organização

A apresentação trata comunicação; a aplicação coordena os casos de uso; o domínio valida regras; a infraestrutura conhece banco e SMTP. As interfaces `ManutencaoRepositorio` e `Notificador` reduzem a dependência do serviço em relação às tecnologias concretas.

Essa separação permite testar regras com memória e notificadores simulados e concentra alterações técnicas em componentes específicos. Por exemplo, mudar o acesso ao banco não deve exigir modificar a regra que impede concluir um chamado sem diagnóstico e intervenção.

O custo é manter contratos, conversões entre dados persistidos e entidades, esquemas de entrada e saída e a configuração que conecta as implementações. Uma separação pouco criteriosa pode acrescentar classes que apenas repassam chamadas, sem melhorar o entendimento ou a capacidade de alteração.

**Justificativa da escolha:** persistência e comunicação externa são variações concretas do sistema. Isolá-las possui utilidade para testes e evolução, enquanto a separação entre coordenação e regras torna as responsabilidades verificáveis.

**Como controlar o custo:** criar abstrações para necessidades identificadas e verificar as dependências entre camadas. Interfaces não eliminam acoplamento: mudanças nos contratos, nos erros ou no significado dos dados podem afetar seus consumidores.

## 5. Serviço e repositório abrangentes: coordenação simples e menor coesão

`ManutencaoService` reúne os casos de uso do atendimento e o processamento de notificações. `ManutencaoRepositorio` oferece as consultas e gravações necessárias a esse serviço. A escolha mantém poucos pontos de coordenação e explicita a operação que salva chamado, auditoria e notificação conjuntamente.

Entretanto, composição de mensagens, autorização, consultas e coordenação de atendimento possuem motivos distintos de alteração. A concentração reduz a coesão do serviço. O contrato de repositório também é mais amplo do que o necessário ao processamento de notificações, que utiliza apenas parte de suas operações.

**Justificativa da escolha:** os casos de uso pertencem ao mesmo processo e o escopo é reduzido. Um serviço e um contrato abrangentes mantêm a colaboração simples, desde que regras de domínio, SQL e SMTP não sejam incorporados ao serviço.

**Como controlar o custo:** observar mudanças independentes e frequentes. Se notificações ou consultas passarem a evoluir separadamente, serviços e interfaces menores poderão ser introduzidos. Separar interfaces não impede compartilhar uma implementação ou realizar uma transação; a abrangência atual é uma escolha de simplicidade, não uma exigência do PostgreSQL.

## 6. PostgreSQL e transações locais: consistência e dependência do banco

Salvar chamado, auditoria e notificação na mesma transação evita estados parciais, como uma conclusão persistida sem seu histórico ou sem a comunicação pendente. Chaves estrangeiras e restrições complementam as regras do domínio.

Essa garantia traz custos: as operações precisam participar do mesmo contexto transacional, gravações concorrentes podem disputar recursos e mudanças no esquema precisam ser coordenadas com a aplicação. O banco também concentra uma dependência de disponibilidade do sistema.

**Justificativa da escolha:** o atendimento exige relações consistentes entre equipamentos, usuários, chamados e registros associados. Transações locais oferecem um mecanismo direto para preservar essas relações sem coordenação distribuída.

**Como controlar o custo:** manter transações curtas e excluir o envio SMTP de seu interior, utilizar índices adequados às consultas e planejar a evolução do esquema. Scripts de criação inicial não substituem migrações que preservem dados existentes. Uma troca de persistência deve manter as garantias do contrato, e não apenas seus métodos.

## 7. SQL direto: controle explícito e trabalho manual

O acesso com `psycopg` mantém visíveis as consultas, os filtros e os limites das transações. A infraestrutura concentra a conversão entre registros do banco e objetos do domínio, sem exigir um conjunto adicional de classes de mapeamento de ORM.

O custo é escrever e manter essas conversões, atualizar consultas quando o esquema muda e verificar o número de acessos necessários para reconstruir os objetos. Recuperar dados associados com várias consultas pode se tornar oneroso em listagens grandes.

**Justificativa da escolha:** o esquema e o conjunto de operações têm tamanho compatível com SQL explícito, o que facilita explicar e verificar a persistência no trabalho.

**Como controlar o custo:** utilizar parâmetros nas consultas, testes de integração e medições quando o volume justificar otimizações. A opção por SQL direto não oferece desempenho superior por si só; o resultado depende das consultas, índices e padrões de acesso.

## 8. Auditoria e modelo de domínio: rastreabilidade e volume de registros

O domínio mantém diagnóstico e descrição da intervenção no próprio `Chamado`, além de uma lista de técnicos. Essa organização reduz o número de entidades e associações a persistir. `RegistroAuditoria` preserva as mudanças relevantes, com autor, instante e valores anteriores e novos.

O custo dessa simplificação é que não há uma coleção de intervenções independentes nem atribuições com períodos próprios. Reconstruir alterações anteriores depende da completude da auditoria, e consultas analíticas sobre cada atividade técnica ficam menos diretas. Preservar o histórico também faz a tabela de auditoria crescer ao longo do tempo.

**Justificativa da escolha:** o modelo concentra a solução registrada no atendimento e utiliza auditoria para rastrear suas mudanças, mantendo um conjunto pequeno de entidades. Isso é suficiente apenas para o escopo que trata a intervenção como informação do chamado, sem exigir várias atividades independentes com estrutura própria.

**Como controlar o custo:** registrar alterações relevantes na mesma transação do chamado, definir claramente os dados auditados e impedir a sobrescrita dos registros. O gatilho que protege a auditoria não cria automaticamente registros ausentes. Se surgirem requisitos de múltiplas intervenções ou períodos de atribuição consultáveis individualmente, será necessário evoluir o domínio; acrescentar texto à auditoria não equivale a modelar essas atividades.

## 9. Notificações posteriores: independência do SMTP e consistência eventual

A operação confirma o atendimento e sua notificação pendente antes de tentar o envio externo. Assim, a indisponibilidade do SMTP não impede a abertura ou conclusão, contribuindo para o ASR03.

A consequência é que a confirmação do atendimento e a entrega da mensagem acontecem em momentos diferentes. A pendência precisa ser consultada, processada e atualizada, e pode ocorrer repetição se o SMTP aceitar a mensagem e a aplicação falhar antes de registrar o sucesso.

**Justificativa da escolha:** manter o atendimento disponível é mais importante do que aguardar uma integração externa para confirmar a operação. A gravação conjunta evita depender de uma tentativa de envio sem registro durável.

**Como controlar o custo:** persistir estado e tentativas, coordenar o processamento e não apresentar o sucesso da operação como prova de entrega do e-mail. `ENVIADA` significa aceitação pelo serviço SMTP, não leitura pelo destinatário. Reservas temporárias reduzem concorrência, mas não garantem entrega exatamente uma vez.

## 10. Fila no banco e agendador interno: operação simples e recursos compartilhados

As notificações pendentes ficam no PostgreSQL, e `AgendadorNotificacoes` aciona seu processamento a cada dez segundos dentro da aplicação. Isso evita introduzir um serviço adicional de mensageria e utiliza a mesma persistência necessária ao atendimento.

Em contrapartida, a consulta periódica gera acessos mesmo quando há poucas mensagens, a entrega aguarda uma rodada de processamento e as tentativas dependem de a aplicação estar ativa. O trabalho de envio compartilha recursos com o backend. O intervalo de dez segundos não constitui garantia de entrega nesse prazo: filas, duração do envio e falhas podem aumentar a espera.

**Justificativa da escolha:** o volume do trabalho não demonstra necessidade de infraestrutura especializada de mensageria. A fila no banco permite explicar e testar persistência e recuperação com menos componentes operacionais.

**Como controlar o custo:** evitar bloquear o atendimento HTTP durante chamadas SMTP, limitar tempo de conexão, tratar falhas de uma rodada e coordenar a seleção de mensagens. Se o volume ou a necessidade de disponibilidade do processador crescerem, será necessário avaliar processamento separado ou outro mecanismo de distribuição.

## 11. Cinco tentativas: controle de repetição e limite de recuperação

A política define `MAX_TENTATIVAS = 5`. Uma falha incrementa o contador; antes do limite, a mensagem permanece `PENDENTE`; ao atingi-lo, passa para `FALHOU` e deixa de ser selecionada automaticamente.

O benefício é limitar o esforço repetido sobre mensagens que continuam falhando e manter um estado explícito de falha. O custo é que uma indisponibilidade temporária prolongada pode esgotar as tentativas. Se o SMTP voltar depois disso, essas mensagens não serão enviadas automaticamente.

**Justificativa da política:** o limite oferece um comportamento simples e verificável para falhas recorrentes. Entretanto, o valor cinco não decorre de uma medição de disponibilidade, e não deve ser apresentado como suficiente para qualquer interrupção do serviço.

**Limite em relação ao ASR03:** o requisito prevê retomada após o restabelecimento da comunicação. Sem reativação das mensagens em `FALHOU`, a política cobre apenas parte desse cenário. Essa é uma limitação a resolver, não uma garantia fornecida pela arquitetura nem uma flexibilização implícita do requisito.

**Como tratar a limitação:** definir reprocessamento explícito, novas tentativas com intervalos progressivos ou outra política que permita recuperar falhas temporárias prolongadas. Essas medidas precisam ser implementadas e verificadas; não devem ser consideradas existentes apenas por serem possibilidades de evolução.

## 12. Síntese da decisão

A arquitetura prioriza compartilhamento centralizado, consistência transacional e separação das regras em relação às tecnologias. Aceita implantação conjunta, dependência do backend e do banco e maior concentração em alguns contratos para manter a complexidade compatível com o trabalho.

Os principais benefícios para os ASRs são a persistência conjunta da auditoria, a autorização no servidor e o registro durável de notificações. Sua efetividade exige regras corretas e testes das operações. Em particular, a concentração de responsabilidades deve ser acompanhada durante a evolução, e a recuperação após o limite de tentativas permanece uma restrição concreta à confiabilidade pretendida.
