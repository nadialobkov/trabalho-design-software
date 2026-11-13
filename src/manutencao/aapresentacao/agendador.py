import asyncio
import logging

from manutencao.aplicacao.servico import ManutencaoService


logger = logging.getLogger(__name__)


class AgendadorNotificacoes:
    """Input adapter driven by the clock: resends pending notifications (UC09)."""

    def __init__(self, servico: ManutencaoService, intervalo_segundos: float) -> None:
        self.servico = servico
        self.intervalo_segundos = intervalo_segundos

    def executar(self) -> None:
        """Run one round of resending."""
        self.servico.reenviar_notificacoes()

    async def rodar(self) -> None:
        """Run a round every `intervalo_segundos` until the app stops."""
        while True:
            try:
                # Sending e-mail blocks, so it runs in a thread and HTTP
                # requests keep being served meanwhile.
                await asyncio.to_thread(self.executar)
            except Exception:
                # One bad round must not stop the scheduler for good.
                logger.exception("Failed to resend notifications.")
            await asyncio.sleep(self.intervalo_segundos)
