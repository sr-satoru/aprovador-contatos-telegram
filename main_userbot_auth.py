#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔐 MAIN USERBOT AUTH - Utilitário de Autenticação Inicial
Executa o fluxo interativo no terminal para login na conta do Telegram via Telethon,
gerando e salvando a sessão no arquivo conta.session.
"""

import sys
import asyncio
import logging
from core.config import load_config
from userbot.client import TelethonClientManager
from userbot.authenticator import UserBotAuthenticator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("UserBotAuth")


async def main():
    print("=" * 60)
    print("🔐 TELETHON USERBOT - AUTENTICAÇÃO E CHECAGEM DE CONTA")
    print("=" * 60)

    config = load_config()

    if not config.userbot.is_configured():
        print("\n❌ ERRO: Credenciais do UserBot não configuradas!")
        print("Configure no arquivo .env as seguintes variáveis:")
        print("  API_ID, API_HASH, PHONE_NUMBER")
        print("Consulte o arquivo .env.example para instruções.")
        sys.exit(1)

    client_manager = TelethonClientManager(config.userbot)
    authenticator = UserBotAuthenticator(config.userbot, client_manager)

    # Suporte a flag --check
    if "--check" in sys.argv:
        print("🔍 Verificando status da sessão existente...")
        client = await client_manager.get_client()
        if await client.is_user_authorized():
            me = await client.get_me()
            name = f"{me.first_name or ''} {me.last_name or ''}".strip()
            print(f"✅ UserBot autenticado com sucesso!")
            print(f"👤 Nome: {name}")
            print(f"🆔 ID: {me.id}")
            print(f"📱 Telefone: +{getattr(me, 'phone', config.userbot.phone_number)}")
        else:
            print("❌ UserBot NÃO está autenticado. Execute sem --check para autenticar.")
        await client_manager.disconnect()
        return

    user_info = await authenticator.authenticate_interactive()
    if user_info:
        print("\n" + "=" * 60)
        print("🎉 SUCESSO! A sessão está salva e pronta para uso pelo Bot Controller.")
        print("Agora você pode executar: python3 main_bot.py")
        print("=" * 60)
    else:
        print("\n❌ Não foi possível concluir a autenticação.")

    await client_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
