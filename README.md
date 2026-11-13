# Trabalho Design e Arquitetura de Software (CI1163-2026/2)

## Integrantes
- João Marcelo Caboclo (20221227)
- Luíza (XXX)
- Nadia Luana Lobkov (20232381)

## Tema 5

**Manutenção de equipamentos de laboratório** — Sistema para registrar chamados de manutenção, classificar prioridades, atribuir técnicos, acompanhar intervenções e manter o histórico dos equipamentos.

---

### Link para o [Enunciado](https://ufprvirtual.ufpr.br/pluginfile.php/2959256/mod_resource/content/0/Design_de_software%20%2815%29.pdf)

---

## Como rodar o protótipo

O protótipo é o backend em Python (FastAPI). Ele implementa o UC01 (abrir chamado), o UC02 (consultar chamados) e o envio assíncrono do e-mail de confirmação (UC09). As telas React ficam para uma próxima etapa; por enquanto a API é usada pela página `/docs`.

### O que instalar

| Ferramenta | Para quê | Como instalar |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | Instala o Python 3.12+ e as bibliotecas do projeto | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| PostgreSQL | Banco de dados | Ubuntu/WSL: `sudo apt install postgresql` · Mac: `brew install postgresql@17` · Windows: instalador do site postgresql.org |
| [Mailpit](https://mailpit.axllent.org/) | Caixa de e-mail falsa e local, para ver os e-mails enviados | Linux/WSL: `sudo sh < <(curl -sL https://raw.githubusercontent.com/axllent/mailpit/develop/install.sh)` · Mac: `brew install mailpit` |

Não é preciso Docker.

### Primeira vez

```bash
# 1. Bibliotecas do projeto (cria a pasta .venv)
uv sync

# 2. Um usuário do PostgreSQL com o seu nome de usuário do sistema (pede a senha do sudo)
sudo -u postgres createuser --createdb "$USER"

# 3. Os bancos: um para a aplicação e um para os testes
createdb manutencao
createdb manutencao_teste

# 4. As tabelas e os dados de exemplo
psql -d manutencao -f banco/schema.sql -f banco/dados_exemplo.sql

# 5. As configurações locais (o .env não vai para o git)
cp .env.example .env
```

### Rodar

```bash
mailpit                                      # em um terminal: e-mails em http://localhost:8025
uv run fastapi dev src/manutencao/main.py    # em outro terminal: API em http://localhost:8000
```

Abra `http://localhost:8000/docs`. Não há login: o usuário é informado no cabeçalho `X-Usuario-Id`.

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

### Configurações (`.env`)

| Variável | Sem ela | Com ela |
|---|---|---|
| `DATABASE_URL` | Dados ficam na memória e somem ao parar o servidor | Dados ficam no PostgreSQL |
| `SMTP_HOST` (e `SMTP_PORTA`, `SMTP_REMETENTE`) | E-mails vão para um notificador falso, que não envia nada | E-mails vão para esse servidor SMTP (o Mailpit, localmente) |

Para usar um provedor real, como o Gmail, preencha também `SMTP_USUARIO` e `SMTP_SENHA` (veja o `.env.example`).

Para apagar todos os dados e voltar aos dados de exemplo:

```bash
psql -d manutencao -f banco/schema.sql -f banco/dados_exemplo.sql
```

### Testes

```bash
uv run pytest                                                          # testes sem banco
TEST_DATABASE_URL=postgresql:///manutencao_teste uv run pytest         # inclui os testes do PostgreSQL
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
banco/                # schema.sql (tabelas) e dados_exemplo.sql
docs/                 # requisitos, diagramas e ADRs
```

O Domínio não conhece nenhuma outra camada, e a Aplicação não conhece a Infraestrutura: ela só usa interfaces, que a Infraestrutura implementa. O teste `tests/test_camadas.py` confere essa regra.
