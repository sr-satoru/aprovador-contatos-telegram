"""
Gerenciador de Conexão e Sessão Telethon (MTProto)
Responsável por gerenciar o ciclo de vida do TelegramClient e StringSession.
"""

import os
import logging
from typing import Optional
from telethon import TelegramClient
from telethon.sessions import StringSession
from core.config import UserBotConfig

logger = logging.getLogger(__name__)


class TelethonClientManager:
    """Gerencia a sessão e a conexão física do TelegramClient."""

    def __init__(self, config: UserBotConfig):
        self._config = config
        self._client: Optional[TelegramClient] = None
        self._session_string = self._load_session_string()

    def _load_session_string(self) -> str:
        """Carrega a string de sessão salva em arquivo, se existir."""
        if os.path.exists(self._config.session_file):
            try:
                with open(self._config.session_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        logger.info("Sessão salva encontrada.")
                        return content
            except Exception as e:
                logger.warning(f"Erro ao ler sessão de {self._config.session_file}: {e}")
        return ""

    def save_session_string(self, session_string: str) -> None:
        """Salva a string de sessão no arquivo configurado."""
        try:
            with open(self._config.session_file, "w", encoding="utf-8") as f:
                f.write(session_string.strip())
            self._session_string = session_string.strip()
            logger.info("Sessão salva com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao salvar sessão em {self._config.session_file}: {e}")

    async def get_client(self) -> TelegramClient:
        """Retorna o cliente TelegramClient inicializado e conectado."""
        if self._client is None:
            session = StringSession(self._session_string) if self._session_string else StringSession()
            self._client = TelegramClient(session, self._config.api_id, self._config.api_hash)
            await self._client.connect()
        elif not self._client.is_connected():
            await self._client.connect()
        return self._client

    async def is_authorized(self) -> bool:
        """Verifica se o cliente está autenticado na conta do Telegram."""
        try:
            client = await self.get_client()
            return await client.is_user_authorized()
        except Exception as e:
            logger.warning(f"Erro ao verificar autorização do UserBot: {e}")
            return False

    async def disconnect(self) -> None:
        """Encerra a conexão do cliente Telethon de forma limpa."""
        if self._client and self._client.is_connected():
            await self._client.disconnect()
            logger.info("Cliente UserBot desconectado.")
        self._client = None
