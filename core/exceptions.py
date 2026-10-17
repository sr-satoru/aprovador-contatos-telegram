"""
Exceções de Domínio da Aplicação
"""

class AppException(Exception):
    """Exceção base para erros da aplicação."""
    pass


class ConfigError(AppException):
    """Erro de configuração ou variáveis obrigatórias ausentes."""
    pass


class UserBotError(AppException):
    """Exceção base para erros originados no UserBot MTProto."""
    pass


class UserBotNotConnectedError(UserBotError):
    """Lançada quando uma operação requer o UserBot conectado, mas ele está desconectado."""
    pass


class UserBotAuthenticationError(UserBotError):
    """Lançada quando a autenticação do UserBot falha."""
    pass


class ChannelNotFoundError(AppException):
    """Canal não encontrado ou inacessível pela conta."""
    pass


class ChannelAccessError(AppException):
    """Sem permissões suficientes de administrador no canal."""
    pass


class ApprovalCancelledError(AppException):
    """Operação de aprovação foi cancelada pelo usuário."""
    pass


class FloodWaitTimeoutError(AppException):
    """Telegram impôs um FloodWait além do limite aceitável de espera."""
    def __init__(self, seconds: int):
        self.seconds = seconds
        super().__init__(f"FloodWait imposto pelo Telegram: aguarde {seconds} segundos.")
