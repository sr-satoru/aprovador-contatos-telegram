"""
Handlers Administrativos do Bot - Clean Architecture (Presentation Layer)
Comandos: /start, /status, /delay, /logs
"""

from telegram import Update
from telegram.ext import ContextTypes
from bot.middlewares import check_authorized
from bot import formatters
from core.interfaces import IUserBotGateway, IStorageRepository, ILogRepository
from services.approval_service import ApprovalService


@check_authorized
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Mensagem de boas-vindas e ajuda."""
    user = update.effective_user
    storage: IStorageRepository = context.bot_data["storage"]
    storage.increment_commands_count()

    text = formatters.format_welcome(user.first_name if user else "Administrador")
    await update.message.reply_text(text, parse_mode="Markdown")


@check_authorized
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status - Status geral do sistema e estatísticas."""
    storage: IStorageRepository = context.bot_data["storage"]
    gateway: IUserBotGateway = context.bot_data["gateway"]
    approval_service: ApprovalService = context.bot_data["approval_service"]

    userbot_connected = await gateway.is_authenticated()
    active_count = approval_service.get_active_task_count()
    current_delay = storage.get_delay()
    stats = storage.get_statistics()

    text = formatters.format_status(
        userbot_connected=userbot_connected,
        active_approvals_count=active_count,
        background_tasks_count=active_count,
        current_delay=current_delay,
        stats=stats,
    )
    await update.message.reply_text(text, parse_mode="Markdown")


@check_authorized
async def delay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /delay [VALOR] - Consulta ou altera o delay entre aprovações."""
    storage: IStorageRepository = context.bot_data["storage"]
    logs: ILogRepository = context.bot_data["logs"]

    if not context.args:
        current_delay = storage.get_delay()
        text = formatters.format_delay_info(current_delay)
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    try:
        new_delay = float(context.args[0].replace(",", "."))
        if new_delay < 0:
            await update.message.reply_text("❌ O delay não pode ser negativo!")
            return

        old_delay = storage.get_delay()
        storage.set_delay(new_delay)
        logs.add_log(f"Delay alterado: {old_delay}s → {new_delay}s")

        success_text = f"""✅ *DELAY CONFIGURADO!*

⏱️ *Antes:* {old_delay}s
⏱️ *Agora:* {new_delay}s

💾 Configuração salva!
🔄 O novo delay será usado nas próximas aprovações.

💡 Use `/status` para ver todas as configurações."""
        await update.message.reply_text(success_text, parse_mode="Markdown")

    except ValueError:
        await update.message.reply_text(
            "❌ *Valor inválido*\n\n"
            "Use um número (ex: 1, 0.5, 2.5)\n\n"
            "📝 Exemplo: `/delay 1.5`",
            parse_mode="Markdown",
        )


@check_authorized
async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /logs - Exibe os logs recentes do sistema."""
    logs_repo: ILogRepository = context.bot_data["logs"]
    recent = logs_repo.get_recent_logs(8)
    text = formatters.format_recent_logs(recent)
    await update.message.reply_text(text, parse_mode="Markdown")
