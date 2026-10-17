#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 TELETHON USERBOT (Legacy Bridge & Adapter)
Arquivo de compatibilidade com a versão anterior.
Para novos desenvolvimentos ou execução direta:
- Para autenticação inicial: python3 main_userbot_auth.py
- Para menu no terminal: python3 -m userbot.cli
- Para o bot controlador: python3 main_bot.py
"""

import asyncio
from typing import List, Optional
from core.config import load_config
from storage.json_repository import JsonStorageRepository
from userbot.client import TelethonClientManager
from userbot.authenticator import UserBotAuthenticator
from userbot.gateway import TelethonUserBotGateway
from userbot.cli import UserBotCLI


class TelethonUserBot:
    """
    Adapter de compatibilidade legada.
    Delega chamadas para o TelethonUserBotGateway e JsonStorageRepository da Clean Architecture.
    """

    def __init__(self):
        self.config = load_config()
        self.storage = JsonStorageRepository(
            self.config.bot.config_file, self.config.default_delay
        )
        self.client_manager = TelethonClientManager(self.config.userbot)
        self.authenticator = UserBotAuthenticator(self.config.userbot, self.client_manager)
        self.gateway = TelethonUserBotGateway(self.client_manager)

    @property
    def client(self):
        """Acesso compatível ao client interno se necessário."""
        return self.client_manager._client

    def set_approve_delay(self, delay: float):
        """Configura o delay entre aprovações."""
        self.storage.set_delay(delay)

    async def authenticate(self) -> bool:
        """Autentica o userbot."""
        info = await self.authenticator.authenticate_interactive()
        return bool(info)

    async def get_channel_info(self, channel_input: str) -> Optional[dict]:
        """Obtém informações do canal."""
        info = await self.gateway.get_channel_info(channel_input)
        return info.to_dict() if info else None

    async def get_all_pending_requests(self, channel_id: int, max_requests: int = None) -> List[dict]:
        """Busca todas as solicitações pendentes."""
        requests = await self.gateway.fetch_pending_requests(channel_id, max_requests)
        return [r.to_dict() for r in requests]

    async def approve_all_requests_bot_controller(self, channel_id: int) -> dict:
        """Aprova pedidos em massa via Bot Controller."""
        delay = self.storage.get_delay()
        result = await self.gateway.approve_all_channel_requests(
            channel_id=channel_id,
            approve_delay=delay,
        )
        self.storage.increment_approvals_count(result.approved)
        return result.to_dict()

    async def run(self):
        """Executa a interface de terminal."""
        cli = UserBotCLI()
        await cli.run()


async def main():
    cli = UserBotCLI()
    await cli.run()


if __name__ == "__main__":
    print("ℹ️ Executando CLI do Telethon UserBot (Clean Architecture)\n")
    asyncio.run(main())