import smtplib
from email.message import EmailMessage

from manutencao.aplicacao.interface_notificador import Notificador
from manutencao.dominio.notificacao import Notificacao


class SmtpNotificador(Notificador):
    """Envia notificações por e-mail por meio de um servidor SMTP (RF08).

    No ambiente local, usa o Mailpit na porta 1025, sem autenticação.
    Um provedor como o Gmail precisa de `usuario` e `senha` e usa uma conexão TLS.
    """

    def __init__(
        self,
        host: str,
        porta: int,
        remetente: str,
        usuario: str | None = None,
        senha: str | None = None,
    ) -> None:
        self.host = host
        self.porta = porta
        self.remetente = remetente
        self.usuario = usuario
        self.senha = senha

    def enviar(self, notificacao: Notificacao) -> None:
        mensagem = EmailMessage()
        mensagem["From"] = self.remetente
        mensagem["To"] = notificacao.destinatario
        mensagem["Subject"] = notificacao.assunto
        mensagem.set_content(notificacao.mensagem)

        # Falhas como servidor indisponível, login recusado e tempo limite geram
        # OSError. O serviço registra a falha para retomar o envio depois (ASR03).
        with smtplib.SMTP(self.host, self.porta, timeout=10) as servidor:
            if self.usuario:
                servidor.starttls()
                servidor.login(self.usuario, self.senha or "")
            servidor.send_message(mensagem)
