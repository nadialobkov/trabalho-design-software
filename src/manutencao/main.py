import logging
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


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Lê configurações como DATABASE_URL e SMTP_HOST do .env.
# As variáveis já definidas no ambiente têm prioridade.
load_dotenv()

# Com DATABASE_URL, os dados ficam no PostgreSQL. Sem ela, ficam em memória.
url_banco = os.environ.get("DATABASE_URL")
repo: ManutencaoRepositorio = (
    PostgresManutencaoRepositorio(url_banco)
    if url_banco
    else RepositorioEmMemoria.com_dados_de_exemplo()
)
# Com SMTP_HOST, o envio usa o servidor configurado (Mailpit no Docker).
# Sem essa variável, o envio é simulado.
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
logger.info(
    "Backend configurado com armazenamento em %s e envio de e-mails %s.",
    "PostgreSQL" if url_banco else "memória",
    "por SMTP" if smtp_host else "simulado",
)
servico = ManutencaoService(repo, notificador)
# O agendador espera 10 segundos entre rodadas para facilitar a demonstração.
agendador = AgendadorNotificacoes(servico, intervalo_segundos=10)
app = criar_app(servico, agendador)
