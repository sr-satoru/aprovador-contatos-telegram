"""
Gateway Telethon UserBot - Clean Architecture (Infrastructure Layer)
Implementa IUserBotGateway utilizando MTProto da biblioteca Telethon.
Isola completamente detalhes de baixo nível e chamadas RPC do Telegram.
"""

import asyncio
import logging
from typing import List, Optional, Callable, Awaitable
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import (
    HideChatJoinRequestRequest,
    GetChatInviteImportersRequest,
)
from telethon.tl.types import InputUserEmpty, InputUser, Channel, User
from telethon.errors import FloodWaitError

from core.entities import ChannelInfo, JoinRequest, ApprovalResult
from core.interfaces import IUserBotGateway
from core.exceptions import (
    UserBotNotConnectedError,
    ChannelNotFoundError,
    ApprovalCancelledError,
    FloodWaitTimeoutError,
)
from userbot.client import TelethonClientManager

logger = logging.getLogger(__name__)


class TelethonUserBotGateway(IUserBotGateway):
    """Implementação concreta de IUserBotGateway baseada em Telethon."""

    def __init__(self, client_manager: TelethonClientManager):
        self._manager = client_manager

    async def is_authenticated(self) -> bool:
        return await self._manager.is_authorized()

    async def connect(self) -> bool:
        client = await self._manager.get_client()
        return await client.is_user_authorized()

    async def disconnect(self) -> None:
        await self._manager.disconnect()

    async def _resolve_entity(self, channel_id: int | str):
        """Resolve a entidade do canal pelo ID numérico ou @username."""
        client = await self._manager.get_client()
        if not await client.is_user_authorized():
            raise UserBotNotConnectedError("UserBot não está autenticado no Telegram.")
        try:
            if isinstance(channel_id, str) and not channel_id.lstrip("-").isdigit():
                return await client.get_entity(channel_id)
            return await client.get_entity(int(channel_id))
        except Exception as e:
            logger.error(f"Erro ao resolver entidade do canal {channel_id}: {e}")
            raise ChannelNotFoundError(f"Canal {channel_id} não encontrado ou inacessível: {e}")

    async def get_channel_info(self, channel_id: int | str) -> Optional[ChannelInfo]:
        client = await self._manager.get_client()
        entity = await self._resolve_entity(channel_id)

        if not isinstance(entity, Channel):
            return None

        is_admin = False
        can_invite = False
        participants_count = None

        try:
            full_channel = await client(GetFullChannelRequest(entity))
            participants_count = getattr(full_channel.full_chat, "participants_count", None)
            me = await client.get_me()
            permissions = await client.get_permissions(entity, me)
            is_admin = bool(permissions.is_admin)
            can_invite = bool(permissions.invite_users)
        except Exception as e:
            logger.warning(f"Erro ao obter permissões completas do canal {channel_id}: {e}")

        return ChannelInfo(
            id=entity.id,
            title=entity.title,
            username=entity.username,
            participants_count=participants_count,
            is_admin=is_admin,
            can_invite=can_invite,
            is_broadcast=bool(entity.broadcast),
        )

    async def fetch_pending_requests(
        self, channel_id: int, limit: Optional[int] = None
    ) -> List[JoinRequest]:
        client = await self._manager.get_client()
        entity = await self._resolve_entity(channel_id)

        all_requests: List[JoinRequest] = []
        limit_per_batch = 200
        offset_date = 0
        offset_user = InputUserEmpty()
        batch_count = 0
        max_batches = 100  # Limite de segurança

        logger.info(f"Buscando solicitações de entrada pendentes para o canal {entity.title} ({channel_id})...")

        while batch_count < max_batches:
            batch_count += 1
            try:
                result = await client(
                    GetChatInviteImportersRequest(
                        peer=entity,
                        limit=limit_per_batch,
                        offset_date=offset_date,
                        offset_user=offset_user,
                        requested=True,
                    )
                )

                if not result.importers:
                    break

                users_map = {u.id: u for u in result.users if isinstance(u, User)}

                for importer in result.importers:
                    user_info = users_map.get(importer.user_id)
                    user_name = (
                        f"{user_info.first_name or ''} {user_info.last_name or ''}".strip()
                        if user_info
                        else f"Usuário {importer.user_id}"
                    )
                    username = user_info.username if user_info else None

                    all_requests.append(
                        JoinRequest(
                            user_id=importer.user_id,
                            user_name=user_name,
                            username=username,
                            date=importer.date,
                            about=getattr(importer, "about", "") or "",
                        )
                    )

                    if limit and len(all_requests) >= limit:
                        return all_requests[:limit]

                # Configurar offset para próxima página
                last_importer = result.importers[-1]
                offset_date = int(last_importer.date.timestamp())
                last_user = users_map.get(last_importer.user_id)
                offset_user = last_user if last_user else InputUser(last_importer.user_id, 0)

                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Erro no lote {batch_count} ao buscar pedidos: {e}")
                break

        logger.info(f"Busca concluída: {len(all_requests)} pedidos pendentes encontrados.")
        return all_requests

    async def approve_all_channel_requests(
        self,
        channel_id: int,
        approve_delay: float,
        progress_callback: Optional[Callable[[int, int, int], Awaitable[None]]] = None,
        stop_event: Optional[asyncio.Event] = None,
    ) -> ApprovalResult:
        client = await self._manager.get_client()
        entity = await self._resolve_entity(channel_id)

        approved_total = 0
        failed_total = 0
        round_count = 0
        max_rounds = 50

        logger.info(f"Iniciando aprovação em massa para o canal: {entity.title} ({channel_id})")

        while round_count < max_rounds:
            if stop_event and stop_event.is_set():
                raise ApprovalCancelledError(f"Aprovação cancelada pelo usuário no canal {channel_id}.")

            round_count += 1
            try:
                all_requests = await client(
                    GetChatInviteImportersRequest(
                        peer=entity,
                        limit=200,
                        offset_date=0,
                        offset_user=InputUserEmpty(),
                        requested=True,
                    )
                )

                pending_list = all_requests.importers
                if not pending_list:
                    logger.info("Nenhum pedido restante. Aprovação concluída!")
                    break

                for req in pending_list:
                    if stop_event and stop_event.is_set():
                        raise ApprovalCancelledError(f"Aprovação cancelada durante a execução.")

                    try:
                        await client(
                            HideChatJoinRequestRequest(
                                peer=entity,
                                user_id=req.user_id,
                                approved=True,
                            )
                        )
                        approved_total += 1

                    except FloodWaitError as fwe:
                        logger.warning(f"FloodWait detectado: aguardando {fwe.seconds} segundos...")
                        if fwe.seconds > 120:
                            raise FloodWaitTimeoutError(fwe.seconds)
                        await asyncio.sleep(fwe.seconds)
                        # Re-tentar aprovar este usuário
                        try:
                            await client(
                                HideChatJoinRequestRequest(
                                    peer=entity,
                                    user_id=req.user_id,
                                    approved=True,
                                )
                            )
                            approved_total += 1
                        except Exception:
                            failed_total += 1

                    except Exception as e:
                        err_str = str(e).lower()
                        if "already handled" in err_str or "missing" in err_str:
                            approved_total += 1
                        else:
                            logger.error(f"Erro ao aprovar usuário {req.user_id}: {e}")
                            failed_total += 1

                    if progress_callback:
                        await progress_callback(round_count, approved_total, failed_total)

                    if approve_delay > 0:
                        await asyncio.sleep(approve_delay)

                # Delay entre rodadas para estabilidade
                await asyncio.sleep(1.5)

            except ApprovalCancelledError:
                raise
            except Exception as e:
                logger.error(f"Erro na rodada {round_count}: {e}")
                break

        return ApprovalResult(
            rounds=round_count,
            approved=approved_total,
            failed=failed_total,
            message=f"{approved_total} pedidos aprovados em {round_count} rodadas ({failed_total} falhas).",
        )
