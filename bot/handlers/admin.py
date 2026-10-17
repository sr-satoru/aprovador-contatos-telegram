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
    anti_spam = storage.get_anti_spam_settings()
    stats = storage.get_statistics()

    text = formatters.format_status(
        userbot_connected=userbot_connected,
        active_approvals_count=active_count,
        background_tasks_count=active_count,
        current_delay=current_delay,
        stats=stats,
        anti_spam=anti_spam,
    )
    await update.message.reply_text(text, parse_mode="Markdown")


@check_authorized
async def delay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /delay - Consulta ou altera perfil e faixa anti-spam."""
    storage: IStorageRepository = context.bot_data["storage"]
    logs: ILogRepository = context.bot_data["logs"]

    if not context.args:
        current_delay = storage.get_delay()
        anti_spam = storage.get_anti_spam_settings()
        text = formatters.format_delay_info(current_delay, anti_spam)
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    first_arg = context.args[0].lower().strip()

    # 1. Ativação por nome de perfil
    if first_arg in ("seguro", "balanced", "padrao", "padrão"):
        storage.set_anti_spam_profile("balanced")
        logs.add_log("Perfil Anti-Spam alterado para Seguro (Equilibrado).")
        await update.message.reply_text(
            "🛡️ *PERFIL ANTI-SPAM ATIVADO: SEGURO (EQUILIBRADO)*\n\n"
            "⏱️ Faixa: *1.2s a 2.8s* com jitter randômico\n"
            "☕ Micro-pausa: *4s a 8s a cada 20 membros*\n\n"
            "✅ Recomendado para uso contínuo no Telegram!",
            parse_mode="Markdown",
        )
        return

    elif first_arg in ("rapido", "rápido", "fast"):
        storage.set_anti_spam_profile("fast")
        logs.add_log("Perfil Anti-Spam alterado para Rápido.")
        await update.message.reply_text(
            "⚡ *PERFIL ANTI-SPAM ATIVADO: RÁPIDO*\n\n"
            "⏱️ Faixa: *0.8s a 1.5s* com jitter randômico\n"
            "☕ Micro-pausa: *3s a 5s a cada 30 membros*\n\n"
            "⚠️ Use com moderação em listas curtas para evitar FloodWait.",
            parse_mode="Markdown",
        )
        return

    elif first_arg in ("furtivo", "stealth"):
        storage.set_anti_spam_profile("stealth")
        logs.add_log("Perfil Anti-Spam alterado para Furtivo (Stealth).")
        await update.message.reply_text(
            "🐢 *PERFIL ANTI-SPAM ATIVADO: FURTIVO (STEALTH)*\n\n"
            "⏱️ Faixa: *2.5s a 5.0s* com jitter randômico\n"
            "☕ Micro-pausa: *6s a 12s a cada 15 membros*\n\n"
            "🛡️ Máxima proteção contra restrições em canais sensíveis.",
            parse_mode="Markdown",
        )
        return

    # 2. Definição por faixa de dois valores (ex: /delay 1.0 3.0)
    if len(context.args) >= 2:
        try:
            val_min = float(context.args[0].replace(",", "."))
            val_max = float(context.args[1].replace(",", "."))
            if val_min <= 0 or val_max <= 0:
                await update.message.reply_text("❌ Os valores devem ser maiores que zero!")
                return

            storage.set_anti_spam_range(val_min, val_max)
            settings = storage.get_anti_spam_settings()
            logs.add_log(f"Faixa Anti-Spam configurada: {settings.min_delay}s a {settings.max_delay}s")

            await update.message.reply_text(
                f"✅ *FAIXA ANTI-SPAM PERSONALIZADA CONFIGURADA!*\n\n"
                f"⏱️ Mínimo: *{settings.min_delay}s*\n"
                f"⏱️ Máximo: *{settings.max_delay}s*\n"
                f"🎲 Cada aprovação terá um delay aleatório dentro dessa faixa.\n\n"
                f"💾 Configuração salva!",
                parse_mode="Markdown",
            )
            return
        except ValueError:
            pass

    # 3. Definição por valor médio único (ex: /delay 2)
    try:
        new_delay = float(first_arg.replace(",", "."))
        if new_delay <= 0:
            await update.message.reply_text("❌ O delay deve ser maior que zero!")
            return

        storage.set_delay(new_delay)
        settings = storage.get_anti_spam_settings()
        logs.add_log(f"Delay configurado: média {new_delay}s (faixa {settings.min_delay}s~{settings.max_delay}s)")

        await update.message.reply_text(
            f"✅ *DELAY CONFIGURADO COM JITTER ANTI-SPAM!*\n\n"
            f"🎯 Média: *{new_delay}s*\n"
            f"🎲 Faixa randômica gerada: *{settings.min_delay}s a {settings.max_delay}s*\n\n"
            f"🛡️ O sistema variará automaticamente os segundos para proteger sua conta.\n"
            f"💾 Configuração salva!",
            parse_mode="Markdown",
        )
    except ValueError:
        await update.message.reply_text(
            "❌ *Comando não reconhecido*\n\n"
            "Use uma das opções:\n"
            "• `/delay seguro` (1.2s a 2.8s)\n"
            "• `/delay rapido` (0.8s a 1.5s)\n"
            "• `/delay furtivo` (2.5s a 5.0s)\n"
            "• `/delay 1.0 3.0` (faixa personalizada)\n"
            "• `/delay 2` (valor com variação automática)",
            parse_mode="Markdown",
        )


@check_authorized
async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /logs - Exibe os logs recentes do sistema."""
    logs_repo: ILogRepository = context.bot_data["logs"]
    recent = logs_repo.get_recent_logs(8)
    text = formatters.format_recent_logs(recent)
    await update.message.reply_text(text, parse_mode="Markdown")
