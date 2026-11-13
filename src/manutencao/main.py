import os

from dotenv import load_dotenv

from manutencao.aapresentacao.agendador import AgendadorNotificacoes
from manutencao.aapresentacao.controller import criar_app
from manutencao.aplicacao.interface_notificador import Notificador
from manutencao.aplicacao.interface_repositorio import ManutencaoRepositorio
from manutencao.aplicacao.servico import ManutencaoService
from manutencao.infraestrutura.notificador_fake import NotificadorFake
from manutencao.infraestrutura.notificador_smtp import SmtpNotificador
from manutencao.infraestrutura.repositorio_em_memoria import RepositorioEmMemoria
from manutencao.infraestrutura.repositorio_postgres import PostgresManutencaoRepositorio


# Read settings such as DATABASE_URL and SMTP_HOST from .env (a variable already set in the shell wins).
load_dotenv()

# With DATABASE_URL set, data is stored in PostgreSQL; without it, in memory.
url_banco = os.environ.get("DATABASE_URL")
repo: ManutencaoRepositorio = (
    PostgresManutencaoRepositorio(url_banco)
    if url_banco
    else RepositorioEmMemoria.com_dados_de_exemplo()
)
# With SMTP_HOST set, e-mails go to that server (Mailpit locally); without it, to a fake.
smtp_host = os.environ.get("SMTP_HOST")
notificador: Notificador = (
    SmtpNotificador(
        host=smtp_host,
        porta=int(os.environ.get("SMTP_PORTA", "1025")),
        remetente=os.environ.get("SMTP_REMETENTE", "manutencao@example.com"),
        usuario=os.environ.get("SMTP_USUARIO") or None,
        senha=os.environ.get("SMTP_SENHA") or None,
    )
    if smtp_host
    else NotificadorFake()
)
servico = ManutencaoService(repo, notificador)
# Pending e-mails are sent every 10 seconds (short, so a demo shows it quickly).
agendador = AgendadorNotificacoes(servico, intervalo_segundos=10)
app = criar_app(servico, agendador)
