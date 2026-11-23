import asyncio
import logging

from manutencao.aplicacao.servico import ManutencaoService


logger = logging.getLogger(__name__)


class AgendadorNotificacoes:
    """Dispara periodicamente o envio de notificações pendentes (UC09)."""

    def __init__(self, servico: ManutencaoService, intervalo_segundos: float) -> None:
        self.servico = servico
        self.intervalo_segundos = intervalo_segundos

    def executar(self) -> None:
        """Executa uma rodada de envio."""
        self.servico.reenviar_notificacoes()

    async def rodar(self) -> None:
        """Executa rodadas com pausas de `intervalo_segundos` até a aplicação parar."""
        logger.info(
            "Agendador de notificações iniciado com intervalo de %g segundos.",
            self.intervalo_segundos,
        )
        while True:
            try:
                # O envio bloqueia a execução, então roda em outra thread.
                # Assim, o servidor continua atendendo às requisições HTTP.
                await asyncio.to_thread(self.executar)
            except Exception:
                # Registra a falha e mantém o agendador ativo para a próxima rodada.
                logger.exception("Falha na rodada do agendador de notificações. O agendador tentará novamente.")
            await asyncio.sleep(self.intervalo_segundos)
