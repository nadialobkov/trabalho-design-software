from abc import ABC, abstractmethod

from manutencao.dominio.notificacao import Notificacao


class Notificador(ABC):
    @abstractmethod
    def enviar(self, notificacao: Notificacao) -> None:
        """Raises OSError when the message cannot be sent."""
