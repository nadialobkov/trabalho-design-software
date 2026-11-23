from abc import ABC, abstractmethod

from manutencao.dominio.notificacao import Notificacao


class Notificador(ABC):
    @abstractmethod
    def enviar(self, notificacao: Notificacao) -> None:
        """Lança OSError quando o envio da mensagem falha."""
