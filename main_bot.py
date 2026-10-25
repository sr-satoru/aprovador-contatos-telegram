#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 MAIN BOT CONTROLLER - Ponto de Entrada Oficial
Executa o Telegram Bot Controller (python-telegram-bot) desacoplado do UserBot.
"""

import sys
import logging
from core.config import load_config
from storage.json_repository import JsonStorageRepository
from storage.log_buffer import LogBufferRepository
from userbot.client import TelethonClientManager
from userbot.gateway import TelethonUserBotGateway
from services.progress_tracker import ProgressTracker
from services.channel_service import ChannelService
from services.approval_service import ApprovalService
from services.report_service import ReportService
from bot.app import create_bot_app

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("MainBotController")


def main():
    print("=" * 60)
    print("🤖 INICIANDO TELEGRAM BOT CONTROLLER (Clean Architecture)")
    print("=" * 60)

    # 1. Carregar configurações
    config = load_config()

    # Validar se o BOT_TOKEN está configurado
    if not config.bot.is_configured():
        print("\n❌ ERRO: BOT_TOKEN ou AUTHORIZED_USERS não configurados!")
        print("Configure o arquivo .env (consulte .env.example)")
        sys.exit(1)

    # 2. Inicializar Repositórios de Armazenamento e Logs
    storage = JsonStorageRepository(
        config_filepath=config.bot.config_file,
        default_delay=config.default_delay,
    )
    logs = LogBufferRepository(
        filepath=config.bot.logs_file,
    )
    logs.add_log("Sistema iniciando com arquitetura desacoplada.")

    # 3. Inicializar Gateway do UserBot (Telethon MTProto)
    client_manager = TelethonClientManager(config.userbot)
    gateway = TelethonUserBotGateway(client_manager)

    # 4. Inicializar Serviços de Casos de Uso (Application Layer)
    progress_tracker = ProgressTracker()
    channel_service = ChannelService(gateway=gateway, storage=storage)
    approval_service = ApprovalService(
        gateway=gateway,
        storage=storage,
        log_repository=logs,
        progress_tracker=progress_tracker,
    )
    report_service = ReportService()

    # 5. Criar e Configurar Aplicação do Bot
    try:
        app = create_bot_app(
            config=config,
            gateway=gateway,
            storage=storage,
            logs=logs,
            channel_service=channel_service,
            approval_service=approval_service,
            progress_tracker=progress_tracker,
            report_service=report_service,
        )
    except Exception as e:
        logger.error(f"Falha ao configurar a aplicação do bot: {e}")
        sys.exit(1)

    print("🚀 Bot Controller configurado com sucesso!")
    print(f"👥 Usuários autorizados: {config.bot.authorized_users}")
    print("⚡ Iniciando polling do Telegram Bot...\n")

    try:
        app.run_polling()
    except KeyboardInterrupt:
        print("\n👋 Bot Controller encerrado com sucesso!")
    except Exception as e:
        logger.error(f"Erro na execução do bot: {e}")


if __name__ == "__main__":
    main()
