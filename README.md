# Trabalho Design e Arquitetura de Software (CI1163-2026/2)

## Integrantes
- João Marcelo Caboclo (20221227)
- Luíza Weigert Diapp (20221252)
- Nadia Luana Lobkov (20232381)

## Tema 5

**Manutenção de equipamentos de laboratório** — Sistema para registrar chamados de manutenção, classificar prioridades, atribuir técnicos, acompanhar intervenções e manter o histórico dos equipamentos.

---

### Link para o [Enunciado](https://ufprvirtual.ufpr.br/pluginfile.php/2959256/mod_resource/content/0/Design_de_software%20%2815%29.pdf)

---

## Como rodar o protótipo

O protótipo é o backend em Python (FastAPI). Ele implementa o UC01 (abrir chamado), o UC02 (consultar chamados) e o envio assíncrono do e-mail de confirmação (UC09). As telas React ficam para uma próxima etapa; por enquanto a API é usada pela página `/docs`.

### O que instalar

| Ferramenta | Para quê |
|---|---|
| [Docker](https://docs.docker.com/get-docker/) com Docker Compose | Sobe a aplicação, o PostgreSQL e o Mailpit (caixa de e-mail falsa) |
| [uv](https://docs.astral.sh/uv/) (opcional) | Só para rodar os testes ou a API fora do Docker: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

Não é preciso instalar PostgreSQL nem Mailpit: eles rodam em contêineres.

### Rodar

```bash
docker compose up --build
```

O comando sobe três serviços ao mesmo tempo:

| Serviço | O que é | Endereço |
|---|---|---|
| `app` | O backend (o monólito) | `http://localhost:7555/docs` |
| `db` | PostgreSQL 18, já com as tabelas e os dados de exemplo | `localhost:5433` |
| `mailpit` | Caixa de e-mail falsa | `http://localhost:8025` |

O banco é criado na primeira vez, a partir de `banco/schema.sql` e `banco/dados_exemplo.sql`. Os dados continuam salvos entre uma execução e outra.

Para parar: `Ctrl+C`, ou `docker compose down`. Para apagar todos os dados e voltar aos dados de exemplo: `docker compose down -v`.

Depois de mudar o código, rode `docker compose up --build` de novo.

Abra `http://localhost:7555/docs`. Não há login: o usuário é informado no cabeçalho `X-Usuario-Id`.

| id | Usuário | Papel | Departamento |
|---|---|---|---|
| 1 | Ana | Solicitante | — |
| 2 | Bruno | Técnico | Elétrica |
| 3 | Carla | Coordenadora | Elétrica |
| 4 | Davi | Técnico | Óptica |
| 5 | Eva | Solicitante | — |

Equipamentos: 10 Osciloscópio e 11 Fonte de bancada (Elétrica), 12 Microscópio (Óptica).

Exemplo de corpo para `POST /chamados`:

```json
{"equipamento_id": 12, "descricao_problema": "O microscópio não liga", "data_ocorrencia": "2026-11-10"}
```

O chamado é salvo na hora e o e-mail fica na fila como `PENDENTE`. Em até 10 segundos o agendador envia o e-mail, que aparece no Mailpit.

### Rodar a API fora do Docker (opcional)

Útil durante o desenvolvimento, porque o servidor reinicia sozinho a cada mudança no código. O banco e o Mailpit continuam no Docker:

```bash
uv sync                                       # primeira vez: cria a pasta .venv
cp .env.example .env                          # primeira vez: configurações locais (não vão para o git)
docker compose up -d db mailpit               # só o banco e o Mailpit
uv run fastapi dev src/manutencao/main.py --port 7555   # API em http://localhost:7555
```

O `.env` diz onde estão o banco e o servidor de e-mail:

| Variável | Sem ela | Com ela |
|---|---|---|
| `DATABASE_URL` | Dados ficam na memória e somem ao parar o servidor | Dados ficam no PostgreSQL |
| `SMTP_HOST` (e `SMTP_PORTA`, `SMTP_REMETENTE`) | E-mails vão para um notificador falso, que não envia nada | E-mails vão para esse servidor SMTP (o Mailpit) |

Para usar um provedor real, como o Gmail, preencha também `SMTP_USUARIO` e `SMTP_SENHA` (veja o `.env.example`).

### Testes

```bash
uv run pytest                                  # testes sem banco
docker compose up -d db                        # para os testes do PostgreSQL:
TEST_DATABASE_URL=postgresql://manutencao:manutencao@localhost:5433/manutencao_teste uv run pytest
```

Os testes do PostgreSQL apagam e recriam o banco `manutencao_teste`. Nunca use o banco `manutencao` neles.

### Organização do código

```text
src/manutencao/
├── aapresentacao/    # Apresentação: rotas HTTP (controller) e agendador de e-mails
├── aplicacao/        # Aplicação: ManutencaoService e as interfaces (repositório, notificador)
├── dominio/          # Domínio: Chamado, Usuario, Equipamento... e as regras de negócio
├── infraestrutura/   # Infraestrutura: PostgreSQL, memória, SMTP e notificador falso
└── main.py           # Escolhe as implementações (pelo .env) e monta a aplicação
banco/                # schema.sql (tabelas), dados_exemplo.sql e criar_banco_teste.sql
docker-compose.yml    # sobe app + PostgreSQL + Mailpit
Dockerfile            # imagem do backend
docs/                 # requisitos, diagramas e ADRs
```

O Domínio não conhece nenhuma outra camada, e a Aplicação não conhece a Infraestrutura: ela só usa interfaces, que a Infraestrutura implementa. O teste `tests/test_camadas.py` confere essa regra.
