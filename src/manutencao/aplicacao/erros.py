class AcessoNegado(Exception):
    """Usuário ausente, desconhecido ou sem permissão para a ação (ASR02)."""


class EquipamentoNaoEncontrado(Exception):
    """O ID do equipamento informado não existe (RN01)."""
