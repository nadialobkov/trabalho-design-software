# Requisitos — Sistema de manutenção de equipamentos de laboratório


## 1. Requisitos funcionais

### RF01 — Registrar chamado de manutenção

O sistema deve permitir que o solicitante registre um chamado de manutenção, informando o equipamento, a descrição do problema e a data da ocorrência. O registro deve permitir a inclusão de informações adicionais e identificar o solicitante e a data e hora de abertura.

**Justificativa:** formalizar o pedido de manutenção e reunir as informações necessárias para iniciar o atendimento.

### RF02 — Consultar chamados

O sistema deve permitir que usuários autorizados consultem os chamados registrados, incluindo sua descrição, equipamento, prioridade, departamento responsável, técnicos atribuídos e estado atual.

**Justificativa:** permitir o acompanhamento das solicitações e do andamento dos atendimentos.

### RF03 — Filtrar chamados

O sistema deve permitir a filtragem dos chamados por equipamento, prioridade, técnico responsável, estado, período de abertura, solicitante e departamento responsável. Os filtros devem poder ser utilizados individualmente ou em conjunto.

**Justificativa:** facilitar a localização de chamados e o acompanhamento das demandas de manutenção.

### RF04 — Definir e alterar a prioridade do chamado

O sistema deve permitir que o coordenador de manutenção responsável classifique ou altere a prioridade de um chamado entre baixa, média, alta e crítica.

**Justificativa:** organizar o atendimento conforme a urgência do problema e seu impacto nas atividades do laboratório.

### RF05 — Atribuir técnicos ao chamado

O sistema deve permitir que o coordenador de manutenção atribua técnicos autorizados aos chamados sob responsabilidade de seu departamento.

**Justificativa:** distribuir os atendimentos considerando as competências e a disponibilidade dos técnicos.

### RF06 — Consultar o histórico de manutenção do equipamento

O sistema deve permitir que usuários autorizados consultem o histórico de manutenção de um equipamento, incluindo os chamados anteriores, as descrições dos problemas, as datas das ocorrências, os diagnósticos e as intervenções registradas, os técnicos responsáveis e as datas de conclusão, quando disponíveis.

**Justificativa:** apoiar a identificação de problemas recorrentes e a consulta às soluções adotadas anteriormente.

### RF07 — Concluir chamado

O sistema deve permitir que um técnico atribuído ao chamado conclua o atendimento. Na conclusão, o técnico deve registrar o diagnóstico, indicando a causa encontrada, e a intervenção realizada, descrevendo como o problema foi resolvido. O chamado não pode ser concluído sem essas duas descrições.

Ao concluir o chamado, o sistema deve registrar automaticamente a data e hora da conclusão e identificar o técnico que realizou essa operação como autor da intervenção.

**Justificativa:** encerrar formalmente o atendimento e manter o registro da solução aplicada ao equipamento.

### RF08 — Notificar o solicitante por e-mail

O sistema deve enviar um e-mail ao solicitante:

- na abertura do chamado, confirmando o registro e informando sua identificação;
- na conclusão do chamado, informando sua identificação e a descrição da intervenção realizada.

**Justificativa:** confirmar ao solicitante que o pedido foi recebido e comunicar a conclusão do atendimento, permitindo a consulta à solução registrada.


### RF09 — Encaminhar chamado para outro departamento

O sistema deve permitir que o coordenador responsável encaminhe um chamado para outro departamento de manutenção, indicando o departamento de destino e a justificativa do encaminhamento. A operação deve preservar o histórico e registrar os responsáveis e a data e hora da transferência.

**Justificativa:** direcionar o atendimento ao departamento com competência para resolver o problema.

### RF10 — Iniciar atendimento do chamado

O sistema deve permitir que um técnico atribuído ao chamado inicie o atendimento, alterando seu estado de Atribuído para Em atendimento. Ao iniciar o atendimento, o sistema deve registrar automaticamente a data e hora do início e identificar o técnico que realizou a operação.

**Justificativa:** indicar que o problema já está sendo tratado e permitir o acompanhamento do andamento do chamado.

## 2. Restrições e regras de negócio

### RN01 — Vínculo obrigatório com equipamento existente

Todo chamado deve estar associado a um equipamento existente no cadastro utilizado pelo sistema. O sistema deve impedir a abertura de chamados sem esse vínculo.

**Justificativa:** preservar a integridade do histórico de manutenção de cada equipamento.

### RN02 — Atribuição exclusiva a técnicos autorizados

O sistema deve impedir que um chamado seja atribuído a um usuário sem função de técnico ou sem autorização para o atendimento.

**Justificativa:** garantir que apenas profissionais habilitados recebam chamados.

### RN03 — Respeito ao fluxo de estados

O sistema deve permitir somente as transições previstas no fluxo de atendimento definido para os chamados.

Aberto → Atribuído → Em atendimento → Concluído.

Nesse fluxo, a passagem direta de Aberto para Concluído deve ser impedida. A conclusão também deve atender à exigência de registro do diagnóstico e da intervenção estabelecida no RF07.

**Justificativa:** evitar estados incompatíveis com o andamento do atendimento e preservar a coerência do histórico.

## 3. Requisitos arquiteturalmente significativos — ASRs

### ASR01 — Rastreabilidade do histórico de manutenção

O sistema deve manter registros de auditoria das alterações de estado, prioridade, atribuição de técnicos e departamento responsável, bem como dos registros e alterações de diagnósticos e intervenções. Cada registro deve identificar o chamado, o autor, a data e hora e, quando aplicável, os valores anteriores e posteriores à alteração.

Alterações posteriores não devem apagar os registros necessários para reconstruir a sequência dos acontecimentos.

**Critério de verificação:** após uma sequência de alterações em um chamado, deve ser possível consultar quem realizou cada operação, quando ela ocorreu e quais informações foram modificadas.

**Impacto arquitetural:** exige uma estratégia consistente de auditoria e persistência do histórico em todas as operações abrangidas.

### ASR02 — Controle de acesso por papel e departamento 

O sistema deve verificar a autorização em cada operação, considerando o papel do usuário e seu vínculo com o chamado ou departamento responsável. A verificação deve ocorrer também nas operações solicitadas diretamente à API.

**Critério de verificação:** uma tentativa de executar uma operação sem a permissão correspondente deve ser recusada, sem alterar os dados do chamado.

**Impacto arquitetural:** exige uma política de autorização aplicada de forma consistente nos pontos de acesso às funcionalidades.

**Visibilidade dos chamados:** o solicitante consulta os chamados que abriu; técnicos e coordenadores consultam os chamados do seu departamento.

**Atendimentos entre departamentos:** cada chamado tem um único departamento responsável. Quando o chamado é encaminhado (RF09), o acesso passa para o departamento de destino: seus técnicos e seu coordenador passam a consultá-lo e atendê-lo, e o departamento de origem deixa de ter acesso. O solicitante continua consultando o chamado, e o encaminhamento fica registrado na auditoria (ASR01).

### ASR03 — Confiabilidade das notificações

O registro e a conclusão de um chamado devem ser preservados mesmo quando o serviço de notificações estiver indisponível. O sistema deve registrar a notificação pendente e realizar novas tentativas de envio após o restabelecimento do serviço.

**Critério de verificação:** ao registrar ou concluir um chamado durante uma indisponibilidade do serviço de notificações, o chamado deve permanecer salvo e a notificação deve continuar disponível para nova tentativa de envio.

**Impacto arquitetural:** exige tratar o registro ou a conclusão do chamado e a entrega da notificação de forma independente, preservando as notificações pendentes.

