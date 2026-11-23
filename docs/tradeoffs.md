# Alternativas e trade-offs

## Arquitetura escolhida

A arquitetura escolhida para o projeto foi uma combinação de **Cliente-Servidor**, **Monólito** e **Camadas**. No arquivo `arquitetura.md` é descrito por qual motivo foi escolhido essas arquiteturas.

```txt
cliente-servidor + monólito modular + camadas
```

## Alternativa A: Microsserviços

A arquitetura **Microsserviços** foi descartada logo no ínicio na discussão do projeto. A princípio, como o sistema vai ser usado na Universidade, essa arquitetura poderia ser interessante, visto que ela permite uma boa **escalabilidade**. Porém, o escopo da proposta foca mais na **consistência e rastreabilidade** das informações. Além disso, tendo em vista o contexto do problema, os principais usuários seriam os servidores da Universidade e **não haverão grandes picos de acesso** pois os pedidos e gerenciamento de manutenção dos equipamento ocorre de maneira contínua durante os semestres, então **não será necessário escalar tanto.**

O fato de nossa equipe atual ser de **três integrantes** dificulta ainda mais a implementação de um sistema de microsserviços, uma vez que este exige uma equipe maior e mais especializada em cada serviço.

Por esses motivos, a escolha da arquitetura **Monólito** se viu mais adequada, pois é robusta, mais simples de implementar, tem os módulos bem organizados e é fácil depurar.


## Alternativa B: Data-Centered

A arquitetura **Data-Centered** foi considerada como alternativa porque o sistema gira em torno de um conjunto relevante de dados compartilhados: equipamentos, chamados, usuários, departamentos, histórico de manutenção, auditoria e notificações. Nesse estilo, o elemento central é um repositório de dados e os componentes do sistema interagem principalmente lendo e escrevendo nesse repositório.

Em uma primeira análise, essa alternativa **poderia ser interessante** porque o sistema precisa manter um histórico centralizado dos chamados e permitir que solicitantes, técnicos e coordenadores consultem informações comuns. Além disso, uma arquitetura centrada em dados favorece a integração entre diferentes componentes e facilita a criação de consultas, relatórios e visões sobre os mesmos dados. Se houvesse vários sistemas independentes precisando compartilhar a mesma base (por exemplo, um sistema de patrimônio, outro de manutenção e outro de relatórios), a data-centered poderia ser uma opção natural.

Entretanto, no contexto deste projeto, **o problema principal não é apenas compartilhar dados, mas coordenar um fluxo de atendimento com regras bem definidas.** O sistema precisa garantir que um chamado siga o fluxo `Aberto → Atribuído → Em atendimento → Concluído`, que a conclusão só ocorra com diagnóstico e intervenção registrados, que a autorização seja verificada conforme o papel e o departamento do usuário e que toda alteração relevante produza auditoria. Essas responsabilidades pedem um ponto explícito de coordenação, isto é, o serviço de aplicação, e não apenas um banco comum.

## Alternativa C: Event-Driven

A arquitetura **Event-Driven** (orientada a eventos) foi considerada como alternativa porque o domínio possui vários acontecimentos naturais que podem ser representados como eventos: abertura de chamado, definição de prioridade, atribuição de técnico, início do atendimento, conclusão, encaminhamento entre departamentos e envio de notificações. Nesse estilo, componentes publicam eventos em um mecanismo de mensagens (*broker*) e outros componentes reagem a esses eventos de forma assíncrona.

Entretanto, no **contexto deste projeto, o problema principal não é apenas reagir a fatos passados, mas garantir a execução consistente de comandos com regras bem definidas.** O sistema precisa validar se um técnico está atribuído ao chamado, se o chamado está no estado correto, se o usuário tem permissão sobre o departamento responsável e se diagnóstico e intervenção foram informados antes da conclusão. Essas verificações precisam ocorrer antes da operação ser aceita, e não apenas depois, por meio de eventos. Além disso, é introduzida uma **complexidade operacional maior**, que não é ideal visto o pouco tempo para implementação e equipe pequena.


## Alternativa D: Monólito Modular

A arquitetura **Monólito Modular** foi considerada porque permite organizar o sistema por capacidades de negócio, como gestão de chamados, equipamentos, usuários e departamentos e notificações. Cada módulo possui responsabilidades delimitadas e contratos de comunicação com os demais, mantendo o backend como uma única aplicação. Essa organização também pode utilizar camadas internamente.

Para uma **versão completa do projeto, com todas as funcionalidades e evolução contínua, o monólito modular seria a escolha mais adequada entre as opções consideradas**. O crescimento das regras de atribuição, intervenções, encaminhamentos e notificações tornaria mais importante estabelecer limites entre essas responsabilidades. A modularização ajudaria a reduzir o impacto das alterações, facilitar testes por capacidade de negócio e distribuir o desenvolvimento entre os integrantes. Esses benefícios seriam obtidos sem a complexidade operacional dos microsserviços, preservando a implantação única e a possibilidade de utilizar transações locais.

Entretanto, **no contexto da implementação deste trabalho, escolhemos um monólito organizado em quatro camadas**, sem estabelecer módulos de negócio independentes. O protótipo implementa uma fatia funcional concentrada na abertura e consulta de chamados e no processamento de notificações. Para esse escopo, as camadas de apresentação, aplicação, domínio e infraestrutura já permitem separar as responsabilidades, demonstrar inversão de dependências e isolar o acesso ao banco e ao serviço de e-mail.

Adotar módulos exigiria definir contratos internos, determinar quais dados pertencem a cada capacidade e controlar as dependências entre elas. Considerando a equipe de três integrantes, o tempo disponível e a quantidade de funcionalidades implementadas, esse esforço adicional teria um benefício limitado para a demonstração. A prioridade foi garantir coerência entre requisitos, regras de negócio, persistência, auditoria e notificações.

Portanto, **o monólito modular não foi descartado por inadequação ao problema, mas adiado por uma questão de escopo e prioridade**. O monólito em camadas mantém a implementação compreensível e permite demonstrar as decisões arquiteturais exigidas. Com a ampliação das funcionalidades, a modularização poderá ser incorporada, exigindo a definição explícita das fronteiras e dos contratos entre as capacidades de negócio.
