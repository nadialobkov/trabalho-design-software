# Análise de evolução do sistema

## 1. Objetivo

**Se uma das principais tecnologias ou integrações utilizadas precisasse ser substituída, quais partes do sistema seriam afetadas?**

Na arquitetura escolhida — monólito, cliente-servidor e quatro camadas — o impacto depende da responsabilidade afetada. Uma mudança de persistência se concentra na infraestrutura e na configuração, enquanto uma nova interface cliente se concentra na apresentação e na comunicação com a API. Essa separação reduz o alcance das mudanças, mas não elimina a necessidade de adaptar contratos, migrar dados e verificar o comportamento.

Foram selecionadas duas evoluções relacionadas à implementação existente:

1. **Substituir PostgreSQL por outro banco relacional**, como MySQL, preservando os casos de uso.
2. **Incluir um aplicativo mobile**, mantendo o cliente web e reutilizando o backend.

A primeira representa uma substituição de tecnologia; a segunda, uma ampliação das formas de acesso. A análise considera a abertura e consulta de chamados, os filtros e o processamento de notificações já disponíveis. Funcionalidades planejadas não passam a existir automaticamente com essas mudanças.

## 2. Mudança A — PostgreSQL para outro banco relacional

### 2.1. Cenário e alcance

A universidade poderia padronizar sua infraestrutura em outro banco relacional ou exigir sua adoção por razões de operação e suporte. A mudança deve preservar os chamados existentes, suas associações, a auditoria e as notificações, além do comportamento esperado pelos serviços.

O serviço de aplicação utiliza `ManutencaoRepositorio`, enquanto `PostgresManutencaoRepositorio` implementa o acesso com SQL e `psycopg`. Essa separação permite construir uma nova implementação sem incorporar o novo banco às regras de manutenção.

### 2.2. Elementos afetados

| Elemento | Alteração necessária |
|---|---|
| Implementação de `ManutencaoRepositorio` | Criar um repositório para o banco escolhido, implementando consultas, filtros, salvamento, auditoria e processamento das pendências |
| Consultas e mapeamento | Adaptar SQL, parâmetros, geração de identificadores, tipos e conversão entre registros e entidades |
| Esquema e scripts em `banco/` | Adequar tabelas, restrições, índices, gatilhos e inicialização ao novo banco |
| Proteção da auditoria | Reproduzir a garantia contra alterações e exclusões indevidas dos registros, utilizando mecanismos apropriados ao banco escolhido |
| Reserva de notificações | Adaptar a seleção concorrente, a reserva temporária e sua liberação; preservar a possibilidade de retomada após interrupções |
| `main.py` e configuração | Instanciar o novo repositório e fornecer suas configurações de conexão |
| Dependências e implantação | Substituir ou complementar `psycopg`, atualizar o arquivo de dependências e seu lock e ajustar o serviço de banco no Docker Compose |
| Dados existentes | Planejar exportação, transformação e importação sem perder identificadores, relações, autoria, datas e situação das notificações |
| Testes de integração e documentação | Verificar o novo banco e atualizar as instruções de execução e configuração |

Alterar somente `DATABASE_URL` não realiza essa substituição. O `main.py` seleciona explicitamente `PostgresManutencaoRepositorio` quando há uma URL configurada; é necessário modificar essa composição e disponibilizar a nova implementação.

### 2.3. Elementos que podem permanecer inalterados

- **Entidades do domínio:** `Chamado`, `Usuario`, `Equipamento`, `Departamento`, `RegistroAuditoria` e `Notificacao`, desde que os dados e seus significados sejam preservados.
- **Casos de uso em `ManutencaoService`:** podem manter as chamadas ao contrato do repositório, se retornos, erros e garantias comportamentais continuarem equivalentes.
- **Controller e esquemas HTTP:** as requisições e respostas não precisam mudar por causa do mecanismo de armazenamento.
- **Telas React:** continuam utilizando os mesmos endpoints e formatos de dados.
- **Contrato e implementação de envio:** `Notificador`, `SmtpNotificador` e `NotificadorFake` não dependem da escolha do banco.
- **Acionamento periódico:** o agendador pode continuar chamando o mesmo caso de uso de processamento de notificações.

A preservação depende do comportamento, não apenas dos nomes dos métodos. Se o novo repositório confirmar parcialmente uma operação que antes era atômica, ele não será uma substituição equivalente.

### 2.4. Decisões que ajudam a mudança

A **inversão de dependências** faz o serviço conhecer a interface, e não o driver PostgreSQL. A **injeção pelo construtor** concentra a escolha da implementação no ponto de inicialização. A **separação em camadas** mantém SQL e conexões fora do domínio e da apresentação.

O repositório em memória e os testes dos casos de uso ajudam a verificar regras independentemente do novo banco. Entretanto, esses testes não substituem a verificação das transações e da concorrência na implementação real.

### 2.5. Decisões que dificultam ou exigem atenção

O **SQL direto** torna o acesso explícito, mas exige adaptação manual. O repositório utiliza construções como `RETURNING`, intervalos e bloqueio de linhas, e o esquema contém uma função de gatilho em PL/pgSQL. Não se deve pressupor que o conjunto desses comandos possa ser transferido sem ajustes para outro banco.

O contrato de persistência também reúne várias responsabilidades. A troca deve contemplar todo o atendimento e as notificações, não apenas a tabela de chamados. Como o banco é compartilhado, a migração precisa preservar as relações entre todos esses registros.

A fila de notificações no banco aumenta o cuidado com a migração: registros pendentes devem continuar processáveis, enquanto mensagens já enviadas não devem ser reenviadas simplesmente por perder seu estado. As reservas temporárias e as garantias transacionais precisam ser revistas no novo mecanismo.

### 2.6. Garantias a verificar

- **ASR01:** chamado e auditoria continuam sendo confirmados juntos; uma falha de gravação não deixa uma operação parcial.
- **ASR02:** os mesmos usuários recebem os mesmos resultados autorizados nas consultas e filtros.
- **ASR03:** notificações pendentes sobrevivem a reinícios e são selecionadas de forma coordenada pelos processadores.
- **Compatibilidade:** identificadores, datas, enumerações e resultados das consultas mantêm o significado esperado pela aplicação.

A substituição preserva a política existente de tentativas; não resolve, por si só, a limitação das mensagens que chegam ao estado `FALHOU`.

## 3. Mudança B — Inclusão de um aplicativo mobile

### 3.1. Cenário e alcance

Técnicos e solicitantes poderiam precisar consultar ou abrir chamados diretamente pelo celular. A evolução consiste em acrescentar um cliente mobile que utilize a mesma API, mantendo as telas web disponíveis.

A implementação já separa as telas React do backend FastAPI. A abertura utiliza `POST /chamados`, e a consulta utiliza `GET /chamados`, com filtros e respostas JSON. Esses contratos constituem a base para reutilizar as funcionalidades no novo cliente.

### 3.2. Elementos afetados

| Elemento | Alteração necessária |
|---|---|
| Apresentação mobile | Criar telas, navegação, formulários, listagem e tratamento dos estados de carregamento e erro |
| Cliente HTTP | Implementar chamadas aos endpoints, configuração do endereço do servidor e tratamento dos códigos de resposta |
| Conectividade e implantação | Disponibilizar um endereço alcançável pelo dispositivo, com configuração de rede e transporte adequados |
| Identificação e autenticação | Definir como o aplicativo obtém e apresenta uma identidade confiável para uso além da demonstração |
| Catálogos de usuários e equipamentos | Avaliar endpoints de consulta para evitar manter cópias fixas dos dados em dois clientes |
| API, se houver necessidades adicionais | Acrescentar apenas as operações e dados que o aplicativo exigir e que ainda não estejam expostos |
| Testes e documentação | Verificar os fluxos no dispositivo, falhas de comunicação, compatibilidade das respostas e regras de acesso |

O cliente web utiliza o caminho relativo `/api`, encaminhado ao backend por nginx ou Vite. Um aplicativo mobile não pode pressupor esse mesmo contexto: deverá usar um endereço configurado para a API ou para o proxy. Além disso, `localhost` no celular identifica o próprio dispositivo. As portas publicadas apenas em `127.0.0.1` no ambiente de demonstração não disponibilizam automaticamente o servidor a outros aparelhos.

Os usuários e equipamentos usados nas telas são mantidos em um catálogo de exemplo no frontend. Repetir esse catálogo no aplicativo seria possível para uma demonstração, mas criaria duas cópias a atualizar. Para uso contínuo, a consulta ao backend evitaria essa divergência e exigiria ampliar a API.

### 3.3. Elementos que podem permanecer inalterados

- **Domínio e regras:** a validação do chamado permanece no servidor e independe do tipo de dispositivo.
- **Serviços de aplicação:** abertura e consulta podem ser reutilizadas sem uma versão específica para mobile.
- **Persistência:** tabelas e repositório PostgreSQL não precisam mudar apenas pela inclusão de outra interface.
- **Auditoria e transações:** continuam sendo executadas pelo backend ao atender às operações.
- **Notificações por e-mail:** podem continuar com o mesmo agendador e notificador; adicionar um aplicativo não obriga a introduzir notificações push.
- **Cliente web:** pode permanecer disponível se os contratos existentes forem preservados.

As telas React voltadas ao navegador não se tornam automaticamente telas de um aplicativo nativo. A reutilização garantida pela arquitetura está nos casos de uso e contratos do backend; o reaproveitamento do código visual dependeria da tecnologia mobile escolhida.

### 3.4. Decisões que ajudam a mudança

A **arquitetura cliente-servidor** permite que diferentes interfaces acessem a mesma aplicação. A **API HTTP/JSON** estabelece uma forma de comunicação independente das telas web, e os **esquemas de entrada e saída** tornam explícitos os dados esperados.

A **autorização no backend** mantém as mesmas restrições para web e mobile. A existência de dois clientes não exige copiar para cada um as decisões sobre quais chamados o usuário pode consultar. Os controles visuais podem orientar a interação, mas o servidor continua responsável por autorizar a operação.

### 3.5. Decisões que dificultam ou exigem atenção

A identificação atual utiliza `X-Usuario-Id`, escolhido na interface. Isso permite demonstrar as regras de visibilidade, mas não comprova a identidade da pessoa. Um aplicativo para uso real precisa de autenticação e de uma adaptação da entrada da API para obter a identidade de maneira confiável. Essa necessidade já existe no cliente web e fica mais evidente ao ampliar o acesso.

A API cobre a fatia funcional de abertura e consulta. Se o aplicativo precisar concluir atendimentos ou atribuir técnicos, será necessário implementar esses casos de uso no backend. Criar uma tela não substitui as operações de aplicação e domínio ainda planejadas.

Falhas de rede também exigem cuidado. Se o aplicativo repetir uma abertura porque não recebeu a resposta, pode criar outro chamado caso a primeira operação tenha sido confirmada. A API atual não define uma chave de idempotência para essa solicitação. Retentativas automáticas de escrita precisam, portanto, de tratamento adicional. Operação offline com sincronização seria outra evolução, fora da simples inclusão de um cliente conectado.

### 3.6. Garantias a verificar

- **ASR01:** as operações feitas pelo aplicativo produzem os mesmos registros de auditoria que as realizadas pela web.
- **ASR02:** os filtros de visibilidade e as recusas de acesso continuam aplicados pelo servidor, independentemente da interface.
- **ASR03:** abrir um chamado pelo aplicativo também preserva sua notificação quando o SMTP está indisponível.
- **Compatibilidade:** ambos os clientes conseguem utilizar os contratos existentes; evoluções da API não quebram a interface web sem planejamento.

## 4. Síntese dos impactos

| Mudança | Principal área afetada | Principal área preservada | Limite da reutilização |
|---|---|---|---|
| PostgreSQL para outro banco relacional | Infraestrutura, esquema, dados, configuração e testes de integração | Domínio, casos de uso e clientes, se os contratos forem mantidos | A nova persistência precisa reproduzir transações, auditoria e coordenação das pendências |
| Inclusão de aplicativo mobile | Apresentação, cliente HTTP, conectividade e identificação; API quando necessário | Casos de uso existentes, domínio, persistência e envio de e-mails | A API cobre apenas as funções disponíveis e a identidade simulada precisa ser revista para uso real |

A organização em camadas e o uso de contratos reduzem a propagação das mudanças, mas não tornam qualquer substituição automática. A evolução deve preservar o significado das operações e suas garantias de rastreabilidade, autorização e recuperação, além de adaptar os detalhes técnicos específicos da tecnologia ou do cliente introduzido.
