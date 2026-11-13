class AcessoNegado(Exception):
    """User is missing, unknown, or not allowed to do the action (ASR02)."""


class EquipamentoNaoEncontrado(Exception):
    """The equipment id does not exist (RN01)."""
