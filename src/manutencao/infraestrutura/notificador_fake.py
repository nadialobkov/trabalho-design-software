from manutencao.aplicacao.interface_notificador import Notificador
from manutencao.dominio.notificacao import Notificacao


class NotificadorFake(Notificador):
    def __init__(self, falhar: bool = False) -> None:
        self.falhar = falhar
        self.enviadas: list[Notificacao] = []

    def enviar(self, notificacao: Notificacao) -> None:
        if self.falhar:
            raise ConnectionError("falha simulada")
        self.enviadas.append(notificacao)
