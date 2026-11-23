# Alternativas e trade-offs

## Arquitetura escolhida

A arquitetura escolhida para o projeto foi uma combinação de **Cliente-Servidor**, **Monólito Modular** e **Camadas**. No arquivo `arquitetura.md` é descrito por qual motivo foi escolhido essas arquiteturas.

```txt
cliente-servidor + monólito modular + camadas
```

## Alternativa A: Microsserviços

A arquitetura **Microsserviços** foi descartada logo no ínicio na discussão do projeto. A princípio, como o sistema vai ser usado na Universidade, essa arquitetura poderia ser interessante, visto que ela permite uma boa **escalabilidade**. Porém, o escopo da proposta foca mais na **consistência e rastreabilidade** das informações. Além disso, tendo em vista o contexto do problema, os principais usuários seriam os servidores da Universidade e **não haverão grandes picos de acesso** pois os pedidos e gerenciamento de manutenção dos equipamento ocorre de maneira contínua durante os semestres, então **não será necessário escalar tanto.**

O fato de nossa equipe atual ser de **três integrantes** dificulta ainda mais a implementação de um sistema de microsserviços, uma vez que este exige uma equipe maior e mais especializada em cada serviço.

Por esses motivos, a escolha da arquitetura **Monólito Modular** se viu mais adequada, pois é robusta, mais simples de implementar, tem os módulos bem organizados e é fácil depurar.


## Alternativa B: Data-Centered

A arquitetura **Data-Centered** foi considerada como alternativa porque o sistema gira em torno de um conjunto relevante de dados compartilhados: equipamentos, chamados, usuários, departamentos, histórico de manutenção, auditoria e notificações. Nesse estilo, o elemento central é um repositório de dados e os componentes do sistema interagem principalmente lendo e escrevendo nesse repositório.

Em uma primeira análise, essa alternativa **poderia ser interessante** porque o sistema precisa manter um histórico centralizado dos chamados e permitir que solicitantes, técnicos e coordenadores consultem informações comuns. Além disso, uma arquitetura centrada em dados favorece a integração entre diferentes componentes e facilita a criação de consultas, relatórios e visões sobre os mesmos dados. Se houvesse vários sistemas independentes precisando compartilhar a mesma base (por exemplo, um sistema de patrimônio, outro de manutenção e outro de relatórios), a data-centered poderia ser uma opção natural.

Entretanto, no contexto deste projeto, **o problema principal não é apenas compartilhar dados, mas coordenar um fluxo de atendimento com regras bem definidas.** O sistema precisa garantir que um chamado siga o fluxo `Aberto → Atribuído → Em atendimento → Concluído`, que a conclusão só ocorra com diagnóstico e intervenção registrados, que a autorização seja verificada conforme o papel e o departamento do usuário e que toda alteração relevante produza auditoria. Essas responsabilidades pedem um ponto explícito de coordenação, isto é, o serviço de aplicação, e não apenas um banco comum.

## Alternativa C: Event-Driven

A arquitetura **Event-Driven** (orientada a eventos) foi considerada como alternativa porque o domínio possui vários acontecimentos naturais que podem ser representados como eventos: abertura de chamado, definição de prioridade, atribuição de técnico, início do atendimento, conclusão, encaminhamento entre departamentos e envio de notificações. Nesse estilo, componentes publicam eventos em um mecanismo de mensagens (*broker*) e outros componentes reagem a esses eventos de forma assíncrona.

Entretanto, no **contexto deste projeto, o problema principal não é apenas reagir a fatos passados, mas garantir a execução consistente de comandos com regras bem definidas.** O sistema precisa validar se um técnico está atribuído ao chamado, se o chamado está no estado correto, se o usuário tem permissão sobre o departamento responsável e se diagnóstico e intervenção foram informados antes da conclusão. Essas verificações precisam ocorrer antes da operação ser aceita, e não apenas depois, por meio de eventos. Além disso, é introduzida uma **complexidade operacional maior**, que não é ideal visto o pouco tempo para implementação e equipe pequena.