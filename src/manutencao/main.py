import os

from dotenv import load_dotenv

from manutencao.aapresentacao.agendador import AgendadorNotificacoes
from manutencao.aapresentacao.controller import criar_app
from manutencao.aplicacao.repositorio import ManutencaoRepositorio
from manutencao.aplicacao.servico import ManutencaoService
from manutencao.infraestrutura.notificador_fake import NotificadorFake
from manutencao.infraestrutura.repositorio_em_memoria import RepositorioEmMemoria
from manutencao.infraestrutura.repositorio_postgres import PostgresManutencaoRepositorio


# Read settings such as DATABASE_URL from .env (a variable already set in the shell wins).
load_dotenv()

# With DATABASE_URL set, data is stored in PostgreSQL; without it, in memory.
url_banco = os.environ.get("DATABASE_URL")
repo: ManutencaoRepositorio = (
    PostgresManutencaoRepositorio(url_banco)
    if url_banco
    else RepositorioEmMemoria.com_dados_de_exemplo()
)
servico = ManutencaoService(repo, NotificadorFake())
# Pending e-mails are sent every 10 seconds (short, so a demo shows it quickly).
agendador = AgendadorNotificacoes(servico, intervalo_segundos=10)
app = criar_app(servico, agendador)
