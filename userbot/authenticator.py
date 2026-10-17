"""
Autenticador Interativo do UserBot (Terminal / CLI)
Responsável por realizar o fluxo de login interativo com SMS e 2FA.
"""

import logging
from typing import Dict, Any, Optional
from telethon.errors import SessionPasswordNeededError
from userbot.client import TelethonClientManager
from core.config import UserBotConfig

logger = logging.getLogger(__name__)


class UserBotAuthenticator:
    """Realiza o processo de autenticação via console/terminal."""

    def __init__(self, config: UserBotConfig, client_manager: TelethonClientManager):
        self._config = config
        self._manager = client_manager

    async def authenticate_interactive(self) -> Optional[Dict[str, Any]]:
        """
        Executa o fluxo de autenticação interativa no terminal.
        Retorna informações do usuário autenticado ou None se cancelado/falhar.
        """
        if not self._config.is_configured():
            print("\n❌ ERRO: Credenciais do UserBot não configuradas!")
            print("Configure o arquivo .env com API_ID, API_HASH e PHONE_NUMBER.")
            return None

        client = await self._manager.get_client()

        # Verificar se já está autenticado via sessão salva
        if await client.is_user_authorized():
            me = await client.get_me()
            info = {
                "id": me.id,
                "name": f"{me.first_name or ''} {me.last_name or ''}".strip(),
                "username": me.username,
                "phone": getattr(me, "phone", self._config.phone_number),
            }
            print(f"\n✅ Sessão existente válida! Conectado como: {info['name']} (ID: {info['id']})")
            return info

        print("\n" + "=" * 55)
        print("🔐 AUTENTICAÇÃO INTERATIVA - TELETHON USERBOT")
        print("=" * 55)
        print(f"📱 Enviando código de verificação para {self._config.phone_number}...")

        await client.send_code_request(self._config.phone_number)
        code = input("🔢 Digite o código recebido no Telegram/SMS: ").strip()

        try:
            await client.sign_in(self._config.phone_number, code)
        except SessionPasswordNeededError:
            print("🔐 Senha de 2 Etapas (2FA) detectada!")
            password = self._config.senha_2fa
            if not password or password == "SUA_SENHA_2FA_AQUI":
                password = input("🔑 Digite sua senha 2FA: ").strip()

            try:
                await client.sign_in(password=password)
                print("✅ 2FA validado com sucesso!")
            except Exception as e:
                print(f"❌ Falha no 2FA: {e}")
                return None
        except Exception as e:
            print(f"❌ Falha no login: {e}")
            return None

        # Salvar a nova sessão gerada
        session_str = client.session.save()
        self._manager.save_session_string(session_str)

        me = await client.get_me()
        user_info = {
            "id": me.id,
            "name": f"{me.first_name or ''} {me.last_name or ''}".strip(),
            "username": me.username,
            "phone": getattr(me, "phone", self._config.phone_number),
        }
        print(f"\n🎉 Autenticação concluída com sucesso! Conectado como: {user_info['name']}")
        return user_info
