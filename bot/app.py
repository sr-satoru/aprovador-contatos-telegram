"""
Aplicação Principal do Bot Controller - Clean Architecture (Presentation Layer)
Configura a Application do python-telegram-bot, registra handlers e injeta dependências.
"""

import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from core.config import AppConfig
from core.interfaces import IUserBotGateway, IStorageRepository, ILogRepository
from services.channel_service import ChannelService
from services.approval_service import ApprovalService
from services.progress_tracker import ProgressTracker
from bot.handlers.admin import start_command, status_command, delay_command, logs_command
from bot.handlers.channels import add_canal_command, canais_command
from bot.handlers.approvals import (
    checar_todos_command,
    aprovar_command,
    progresso_command,
    parar_aprovacao_command,
    handle_text_confirmation,
)

logger = logging.getLogger(__name__)


def create_bot_app(
    config: AppConfig,
    gateway: IUserBotGateway,
    storage: IStorageRepository,
    logs: ILogRepository,
    channel_service: ChannelService,
    approval_service: ApprovalService,
    progress_tracker: ProgressTracker,
) -> Application:
    """Cria e configura a Application do python-telegram-bot com injeção de dependência."""
    if not config.bot.is_configured():
        logger.error("BOT_TOKEN ou AUTHORIZED_USERS não configurados!")
        raise ValueError("Configure BOT_TOKEN e AUTHORIZED_USERS no .env antes de iniciar o bot.")

    app = Application.builder().token(config.bot.token).build()

    # Injeção de dependências no context.bot_data
    app.bot_data["config"] = config
    app.bot_data["authorized_users"] = config.bot.authorized_users
    app.bot_data["gateway"] = gateway
    app.bot_data["storage"] = storage
    app.bot_data["logs"] = logs
    app.bot_data["channel_service"] = channel_service
    app.bot_data["approval_service"] = approval_service
    app.bot_data["progress_tracker"] = progress_tracker

    # Registro de Handlers de Comandos
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("delay", delay_command))
    app.add_handler(CommandHandler("logs", logs_command))

    app.add_handler(CommandHandler("add_canal", add_canal_command))
    app.add_handler(CommandHandler("canais", canais_command))

    app.add_handler(CommandHandler("checar_todos", checar_todos_command))
    app.add_handler(CommandHandler("aprovar", aprovar_command))
    app.add_handler(CommandHandler("progresso", progresso_command))
    app.add_handler(CommandHandler("parar_aprovacao", parar_aprovacao_command))

    # Handler para confirmação via texto (SIM / NAO)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_confirmation))

    logger.info("Bot Controller configurado e handlers registrados com sucesso.")
    return app
