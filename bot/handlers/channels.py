"""
Handlers de Gestão de Canais - Clean Architecture (Presentation Layer)
Comandos: /add_canal, /canais
"""

from telegram import Update
from telegram.ext import ContextTypes
from bot.middlewares import check_authorized
from bot import formatters
from core.interfaces import ILogRepository
from services.channel_service import ChannelService
from services.progress_tracker import ProgressTracker


@check_authorized
async def add_canal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /add_canal ID - Cadastra um novo canal no sistema."""
    if not context.args:
        await update.message.reply_text(
            "📋 *ADICIONAR CANAL*\n\n"
            "Use: `/add_canal ID_DO_CANAL`\n\n"
            "📝 Exemplos:\n"
            "`/add_canal -1001234567890`\n"
            "`/add_canal 1234567890`",
            parse_mode="Markdown",
        )
        return

    raw_input = context.args[0].strip()
    channel_service: ChannelService = context.bot_data["channel_service"]
    logs: ILogRepository = context.bot_data["logs"]

    try:
        channel_input = int(raw_input) if raw_input.lstrip("-").isdigit() else raw_input
        await update.message.reply_text("🔍 Verificando canal com o UserBot...")

        info = await channel_service.add_channel(channel_input)
        saved = channel_service.get_saved_channels()
        logs.add_log(f"Canal adicionado: {info.title} ({info.id})")

        success_text = f"""✅ *Canal adicionado!*

🆔 ID: `{info.id}`
📢 Nome: {info.title}
📊 Total salvos: {len(saved)}

🚀 Use /canais para ver todos"""
        await update.message.reply_text(success_text, parse_mode="Markdown")

    except ValueError:
        await update.message.reply_text("❌ O ID do canal deve ser um número ou @username válido!")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao acessar canal: {e}")


@check_authorized
async def canais_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /canais - Lista todos os canais cadastrados e seu status atual."""
    channel_service: ChannelService = context.bot_data["channel_service"]
    progress_tracker: ProgressTracker = context.bot_data["progress_tracker"]

    saved_channels = channel_service.get_saved_channels()
    active_channel_ids = list(progress_tracker.get_all_active().keys())

    text = formatters.format_channels_list(saved_channels, active_channel_ids)
    await update.message.reply_text(text, parse_mode="Markdown")
