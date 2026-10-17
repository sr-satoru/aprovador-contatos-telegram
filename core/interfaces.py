"""
Contratos e Protocolos (Interfaces) - Clean Architecture
Definições abstratas usando typing.Protocol.
Permitem desacoplamento total e testes automatizados com mocks.
"""

import asyncio
from typing import Protocol, List, Optional, Callable, Awaitable, Dict, Any
from core.entities import ChannelInfo, JoinRequest, ApprovalResult, LogEntry, AntiSpamSettings


class IUserBotGateway(Protocol):
    """
    Interface do Gateway para o UserBot (MTProto).
    Define as operações que o UserBot disponibiliza para a aplicação.
    """
    async def is_authenticated(self) -> bool:
        """Retorna True se o cliente MTProto estiver autenticado e conectado."""
        ...

    async def connect(self) -> bool:
        """Conecta o cliente MTProto usando a sessão salva."""
        ...

    async def disconnect(self) -> None:
        """Encerra a conexão MTProto de forma limpa."""
        ...

    async def get_channel_info(self, channel_id: int | str) -> Optional[ChannelInfo]:
        """Obtém metadados de um canal ou grupo."""
        ...

    async def fetch_pending_requests(
        self,
        channel_id: int,
        limit: Optional[int] = None
    ) -> List[JoinRequest]:
        """Busca todas as solicitações de entrada pendentes de um canal."""
        ...

    async def approve_all_channel_requests(
        self,
        channel_id: int,
        approve_delay: float = 1.0,
        anti_spam: Optional[AntiSpamSettings] = None,
        progress_callback: Optional[Callable[[int, int, int, Optional[str]], Awaitable[None]]] = None,
        stop_event: Optional[asyncio.Event] = None
    ) -> ApprovalResult:
        """
        Executa a aprovação de todos os pedidos pendentes com paginação segura,
        delays randômicos anti-spam, callback assíncrono de progresso e cancelamento cooperativo.
        """
        ...


class IStorageRepository(Protocol):
    """
    Interface para o repositório de dados persistentes (configurações, canais e estatísticas).
    """
    def get_delay(self) -> float: ...
    def set_delay(self, delay: float) -> None: ...
    def get_anti_spam_settings(self) -> AntiSpamSettings: ...
    def set_anti_spam_settings(self, settings: AntiSpamSettings) -> None: ...
    def set_anti_spam_range(self, min_delay: float, max_delay: float) -> None: ...
    def set_anti_spam_profile(self, profile_name: str) -> bool: ...
    def get_saved_channels(self) -> Dict[str, Dict[str, Any]]: ...
    def add_saved_channel(self, channel_id: int, name: str) -> None: ...
    def remove_saved_channel(self, channel_id: int) -> bool: ...
    def get_last_checked(self, channel_id: int) -> List[int]: ...
    def set_last_checked(self, channel_id: int, user_ids: List[int]) -> None: ...
    def clear_last_checked(self, channel_id: int) -> None: ...
    def increment_commands_count(self) -> None: ...
    def increment_approvals_count(self, count: int) -> None: ...
    def get_statistics(self) -> Dict[str, int]: ...


class ILogRepository(Protocol):
    """
    Interface para o repositório de logs.
    """
    def add_log(self, message: str, level: str = "INFO") -> None: ...
    def get_recent_logs(self, limit: int = 8) -> List[LogEntry]: ...
