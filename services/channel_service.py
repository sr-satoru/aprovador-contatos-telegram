"""
Serviço de Gestão de Canais - Clean Architecture (Application Layer)
Orquestra consultas a canais e pedidos pendentes via gateway e repositório.
"""

import logging
from typing import Dict, Any, List
from core.entities import ChannelInfo, JoinRequest
from core.interfaces import IUserBotGateway, IStorageRepository
from core.exceptions import ChannelNotFoundError

logger = logging.getLogger(__name__)


class ChannelService:
    """Caso de uso: Gestão de canais e verificação de pedidos."""

    def __init__(self, gateway: IUserBotGateway, storage: IStorageRepository):
        self._gateway = gateway
        self._storage = storage

    async def add_channel(self, channel_input: int | str) -> ChannelInfo:
        """Resolve metadados do canal via UserBot e salva no repositório."""
        info = await self._gateway.get_channel_info(channel_input)
        if not info:
            raise ChannelNotFoundError(f"Não foi possível obter informações do canal {channel_input}.")

        self._storage.add_saved_channel(info.id, info.title)
        logger.info(f"Canal salvo: {info.title} ({info.id})")
        return info

    def get_saved_channels(self) -> Dict[str, Dict[str, Any]]:
        """Retorna todos os canais salvos no repositório."""
        return self._storage.get_saved_channels()

    def remove_channel(self, channel_id: int) -> bool:
        """Remove canal do repositório."""
        return self._storage.remove_saved_channel(channel_id)

    async def check_channel_requests(
        self, channel_id: int, track_links: bool = False
    ) -> List[JoinRequest]:
        """Busca todas as solicitações pendentes e salva lista para aprovação futura."""
        requests = await self._gateway.fetch_pending_requests(
            channel_id, track_links=track_links
        )
        if requests:
            user_ids = [r.user_id for r in requests]
            self._storage.set_last_checked(channel_id, user_ids)
        else:
            self._storage.clear_last_checked(channel_id)
        return requests

    def get_pending_user_ids(self, channel_id: int) -> List[int]:
        """Retorna IDs de usuários pendentes salvos na última verificação."""
        return self._storage.get_last_checked(channel_id)

    def clear_pending_user_ids(self, channel_id: int) -> None:
        """Limpa a lista de pedidos verificados."""
        self._storage.clear_last_checked(channel_id)
