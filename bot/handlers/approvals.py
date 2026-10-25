"""
Handlers de Aprovação de Pedidos - Clean Architecture (Presentation Layer)
Comandos: /checar_todos, /aprovar, /progresso, /parar_aprovacao e confirmação textual.
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from bot.middlewares import check_authorized
from bot import formatters
from core.interfaces import ILogRepository, IUserBotGateway
from core.entities import ApprovalResult
from services.channel_service import ChannelService
from services.approval_service import ApprovalService
from services.progress_tracker import ProgressTracker
from services.report_service import ReportService

logger = logging.getLogger(__name__)


@check_authorized
async def checar_todos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /checar_todos ID - Pergunta se deseja gerar planilha e checar pedidos."""
    if not context.args:
        await update.message.reply_text(
            "📋 *VERIFICAR PEDIDOS*\n\n"
            "Use: `/checar_todos ID_DO_CANAL`\n\n"
            "📝 Exemplo: `/checar_todos -1001234567890`\n\n"
            "💡 Use /canais para ver seus canais salvos",
            parse_mode="Markdown",
        )
        return

    try:
        channel_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ O ID do canal deve ser um número!")
        return

    approval_service: ApprovalService = context.bot_data["approval_service"]
    gateway: IUserBotGateway = context.bot_data["gateway"]

    if approval_service.is_channel_running(channel_id):
        await update.message.reply_text(
            f"⚠️ Canal está com aprovação em background! Use `/progresso {channel_id}` para ver o status."
        )
        return

    try:
        info = await gateway.get_channel_info(channel_id)
        channel_name = info.title if info else f"Canal {channel_id}"

        prompt_text = formatters.format_check_tracker_prompt(channel_name, channel_id)
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📊 Sim, com Planilha (a cada 100)",
                        callback_data=f"check_report:yes:{channel_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⚡ Não, Apenas Checar",
                        callback_data=f"check_report:no:{channel_id}",
                    )
                ],
            ]
        )

        await update.message.reply_text(
            prompt_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Erro ao preparar checagem do canal {channel_id}: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Erro ao acessar canal: {e}")


@check_authorized
async def handle_check_report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa o clique nos botões de relatório em planilha (Sim ou Não)."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "check_report":
        return

    choice = parts[1]  # 'yes' ou 'no'
    try:
        channel_id = int(parts[2])
    except ValueError:
        return

    approval_service: ApprovalService = context.bot_data["approval_service"]
    channel_service: ChannelService = context.bot_data["channel_service"]
    gateway: IUserBotGateway = context.bot_data["gateway"]
    report_service: ReportService = context.bot_data["report_service"]
    logs: ILogRepository = context.bot_data["logs"]

    if approval_service.is_channel_running(channel_id):
        await query.edit_message_text(
            f"⚠️ Canal está com aprovação em background! Use `/progresso {channel_id}` para ver o status."
        )
        return

    info = await gateway.get_channel_info(channel_id)
    channel_name = info.title if info else f"Canal {channel_id}"

    with_report = (choice == "yes")

    if with_report:
        await query.edit_message_text(
            f"🔍 *Iniciando checagem avançada com rastreamento de links...*\n\n"
            f"🎯 Canal: *{channel_name}*\n"
            f"⏳ Aguarde enquanto mapeamos os convites e pedidos pendentes...",
            parse_mode="Markdown",
        )
    else:
        await query.edit_message_text(
            f"🔍 *Buscando pedidos pendentes via UserBot (modo rápido)...*\n\n"
            f"🎯 Canal: *{channel_name}*",
            parse_mode="Markdown",
        )

    try:
        requests = await channel_service.check_channel_requests(channel_id, track_links=with_report)
        mode_label = "com planilha" if with_report else "simples"
        logs.add_log(f"Verificação ({mode_label}): {len(requests)} pedidos no canal {channel_name} ({channel_id})")

        if not requests:
            await query.message.reply_text(
                f"📋 *RESULTADO - VERIFICAÇÃO*\n\n"
                f"🎯 Canal: *{channel_name}*\n"
                f"🆔 ID: `{channel_id}`\n\n"
                f"⚠️ *0 pedidos pendentes encontrados!*",
                parse_mode="Markdown",
            )
            return

        # Se escolheu gerar relatório em planilhas a cada 100 pessoas
        if with_report:
            batches = report_service.generate_csv_batches(requests, channel_name, batch_size=100)
            total_batches = len(batches)

            await query.message.reply_text(
                f"📊 *GERANDO RELATÓRIO DE LEADS*\n\n"
                f"👥 Total de Pedidos: *{len(requests)}*\n"
                f"📁 Planilhas geradas (a cada 100): *{total_batches} arquivo(s)*\n\n"
                f"⏳ Enviando arquivos...",
                parse_mode="Markdown",
            )

            for idx, (filename, csv_bytes) in enumerate(batches, 1):
                caption = f"📄 Lote {idx}/{total_batches} ({min(idx * 100, len(requests))} membros) - {channel_name}"
                await query.message.reply_document(
                    document=csv_bytes,
                    filename=filename,
                    caption=caption,
                )

        # Resumo visual com instrução para /aprovar
        text = formatters.format_pending_requests(channel_name, channel_id, requests)
        await query.message.reply_text(text)

    except Exception as e:
        logger.error(f"Erro ao verificar pedidos do canal {channel_id}: {e}", exc_info=True)
        await query.message.reply_text(f"❌ Erro ao verificar pedidos: {e}")



@check_authorized
async def aprovar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /aprovar ID - Inicia fluxo de confirmação para aprovação."""
    if not context.args:
        await update.message.reply_text(
            "📋 *APROVAR PEDIDOS*\n\n"
            "Use: `/aprovar ID_DO_CANAL`\n\n"
            "📝 Exemplo: `/aprovar -1001234567890`\n\n"
            "⚠️ Primeiro use `/checar_todos ID` para verificar os pedidos",
            parse_mode="Markdown",
        )
        return

    try:
        channel_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ O ID do canal deve ser um número!")
        return

    approval_service: ApprovalService = context.bot_data["approval_service"]
    channel_service: ChannelService = context.bot_data["channel_service"]
    gateway: IUserBotGateway = context.bot_data["gateway"]

    if approval_service.is_channel_running(channel_id):
        await update.message.reply_text(
            f"⚠️ *Já há aprovação em andamento*\n\n"
            f"Canal ID: `{channel_id}`\n\n"
            f"Use `/progresso {channel_id}` para ver status\n"
            f"Use `/parar_aprovacao {channel_id}` para cancelar",
            parse_mode="Markdown",
        )
        return

    pending_ids = channel_service.get_pending_user_ids(channel_id)
    if not pending_ids:
        await update.message.reply_text(
            f"⚠️ *Nenhum pedido verificado*\n\n"
            f"Use `/checar_todos {channel_id}` primeiro para verificar os pedidos pendentes",
            parse_mode="Markdown",
        )
        return

    info = await gateway.get_channel_info(channel_id)
    channel_name = info.title if info else f"Canal {channel_id}"

    # Salvar estado de confirmação pendente para este usuário
    context.user_data["pending_confirmation"] = {
        "channel_id": channel_id,
        "channel_name": channel_name,
        "requests_count": len(pending_ids),
    }

    text = formatters.format_approval_confirmation(channel_name, channel_id, len(pending_ids))
    await update.message.reply_text(text, parse_mode="Markdown")


@check_authorized
async def progresso_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /progresso ID - Consulta o progresso da aprovação em andamento."""
    if not context.args:
        await update.message.reply_text(
            "📋 *VER PROGRESSO*\n\n"
            "Use: `/progresso ID_DO_CANAL`\n\n"
            "📝 Exemplo: `/progresso -1001234567890`",
            parse_mode="Markdown",
        )
        return

    try:
        channel_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ O ID do canal deve ser um número!")
        return

    progress_tracker: ProgressTracker = context.bot_data["progress_tracker"]
    prog = progress_tracker.get_progress(channel_id)

    if not prog and not progress_tracker.is_active(channel_id):
        await update.message.reply_text(
            f"⚠️ *Nenhuma aprovação em andamento*\n\n"
            f"Canal ID: `{channel_id}`\n\n"
            f"Use `/aprovar {channel_id}` para iniciar aprovação",
            parse_mode="Markdown",
        )
        return

    text = formatters.format_progress(prog, channel_id)
    await update.message.reply_text(text, parse_mode="Markdown")


@check_authorized
async def parar_aprovacao_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /parar_aprovacao ID - Interrompe uma aprovação ativa."""
    if not context.args:
        await update.message.reply_text(
            "📋 *PARAR APROVAÇÃO*\n\n"
            "Use: `/parar_aprovacao ID_DO_CANAL`\n\n"
            "📝 Exemplo: `/parar_aprovacao -1001234567890`",
            parse_mode="Markdown",
        )
        return

    try:
        channel_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ O ID do canal deve ser um número!")
        return

    approval_service: ApprovalService = context.bot_data["approval_service"]
    if approval_service.cancel_approval(channel_id):
        await update.message.reply_text(
            f"🛑 *APROVAÇÃO CANCELADA*\n\n"
            f"🆔 Canal ID: `{channel_id}`\n\n"
            f"✅ A solicitação de parada foi enviada com sucesso!",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"⚠️ *Nenhuma aprovação ativa para o canal {channel_id}*",
            parse_mode="Markdown",
        )


@check_authorized
async def handle_text_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de mensagens de texto normais para confirmar aprovações (SIM / NAO)."""
    if not update.message or not update.message.text:
        return

    confirmation_data = context.user_data.get("pending_confirmation")
    if not confirmation_data:
        return

    message_text = update.message.text.upper().strip()
    channel_id = confirmation_data["channel_id"]
    channel_name = confirmation_data["channel_name"]
    approval_service: ApprovalService = context.bot_data["approval_service"]

    # Confirmação Positiva
    if message_text in ["SIM", "S", "YES", "Y", "APROVAR", "CONFIRMAR"]:
        del context.user_data["pending_confirmation"]

        await update.message.reply_text(
            f"🚀 *APROVAÇÃO INICIADA EM BACKGROUND*\n\n"
            f"🎯 Canal: {channel_name}\n"
            f"🆔 ID: `{channel_id}`\n"
            f"👥 Pedidos: {confirmation_data['requests_count']}\n\n"
            f"⚡ **O BOT CONTINUA RESPONDENDO** outros comandos!\n\n"
            f"Use `/progresso {channel_id}` para acompanhar\n"
            f"Use `/parar_aprovacao {channel_id}` para cancelar",
            parse_mode="Markdown",
        )

        original_message = update.message

        async def on_success(result: ApprovalResult):
            text = formatters.format_approval_result(channel_name, channel_id, result)
            await original_message.reply_text(text, parse_mode="Markdown")

        async def on_error(err: Exception):
            await original_message.reply_text(
                f"❌ *Erro na aprovação do canal {channel_name}:*\n{err}",
                parse_mode="Markdown",
            )

        async def on_cancelled():
            await original_message.reply_text(
                f"🛑 *APROVAÇÃO CANCELADA*\n\n"
                f"🎯 Canal: {channel_name}\n"
                f"🆔 ID: `{channel_id}`\n\n"
                f"⚠️ Processo interrompido com sucesso.",
                parse_mode="Markdown",
            )

        started = approval_service.start_background_approval(
            channel_id=channel_id,
            channel_name=channel_name,
            on_success=on_success,
            on_error=on_error,
            on_cancelled=on_cancelled,
        )

        if not started:
            await update.message.reply_text("⚠️ Já existe uma tarefa de aprovação em andamento para este canal!")

    # Confirmação Negativa
    elif message_text in ["NAO", "NÃO", "N", "NO", "CANCELAR", "PARAR"]:
        del context.user_data["pending_confirmation"]
        await update.message.reply_text(
            f"❌ *APROVAÇÃO CANCELADA*\n\n"
            f"🎯 Canal: {channel_name}\n"
            f"🆔 ID: `{channel_id}`\n\n"
            f"✅ Nenhum pedido foi aprovado.",
            parse_mode="Markdown",
        )

    else:
        await update.message.reply_text(
            f"⚠️ *Resposta não reconhecida*\n\n"
            f"Digite exatamente:\n"
            f"**SIM** - para confirmar aprovação\n"
            f"**NAO** - para cancelar\n\n"
            f"Canal: {channel_name}",
            parse_mode="Markdown",
        )
