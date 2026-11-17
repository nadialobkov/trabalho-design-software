# Alternativas e trade-offs

## Arquitetura escolhida

A arquitetura escolhida para o projeto foi uma combinação de **Cliente-Servidor**, **Monólito Modular** e **Camadas**. No arquivo `arquitetura.md` é descrito por qual motivo foi escolhido essas arquiteturas.

## Alternativa A: Microsserviços

A arquitetura **Microsserviços** foi descartada logo no ínicio na discussão do projeto. A princípio, como o sistema vai ser usado na Universidade, esta arquitetura poderia ser interessante, visto que ela permite uma boa **escalabilidade**. Porém, o escopo da proposta foca mais na **consistência** das informações. Além disso, tendo em vista o contexto do problema, os principais usuários seriam os servidores da Universidade e não haverão grandes picos de acesso pois os pedidos e gerenciamento de manutenção dos equipamentos é relacionado de maneira contínua, então **não será necessário escalar tanto.**

O fato de nossa equipe atual ser de **três integrantes** dificulta ainda mais a implementação de um sistema de microsserviços, uma vez que este exige uma equipe maior e mais especializada em cada serviço.

Por esses motivos, a escolha da arquitetura **Monólito Modular** se viu mais adequada, pois é mais simples de implementar, tem os módulos bem organizados e é fácil depurar.

## Alternativa B: 