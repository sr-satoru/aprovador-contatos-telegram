"""
Formatadores de Mensagens - Clean Architecture (Presentation Layer)
Centraliza a estilização visual rica (Markdown e emojis) das respostas do bot.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from core.entities import JoinRequest, ApprovalProgress, ApprovalResult, LogEntry, AntiSpamSettings


def format_welcome(first_name: str) -> str:
    return f"""🤖 *BOT CONTROLLER ATIVO*

👋 Olá {first_name}!

🚀 *COMANDOS DISPONÍVEIS:*
/add\\_canal ID - Adicionar canal
/canais - Listar meus canais
/checar\\_todos ID - Verificar pedidos
/aprovar ID - Aprovar pedidos
/progresso ID - Ver progresso da aprovação
/parar\\_aprovacao ID - Parar aprovação
/delay VALOR - Configurar delay / anti-spam
/status - Status do sistema
/logs - Ver logs

🔥 *Sistema de aprovação via bot em background com Anti-Spam!*"""


def format_status(
    userbot_connected: bool,
    active_approvals_count: int,
    background_tasks_count: int,
    current_delay: float,
    stats: Dict[str, int],
    anti_spam: Optional[AntiSpamSettings] = None,
) -> str:
    userbot_status = "🟢 Conectado" if userbot_connected else "🔴 Desconectado"
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    anti_spam_text = ""
    if anti_spam:
        mode_labels = {
            "balanced": "🛡️ Seguro (Equilibrado)",
            "fast": "⚡ Rápido",
            "stealth": "🐢 Furtivo (Stealth)",
            "custom": "🛠️ Personalizado",
        }
        label = mode_labels.get(anti_spam.mode, anti_spam.mode.capitalize())
        pause_txt = f"\n☕ Pausas de lote: a cada {anti_spam.batch_size} membros ({anti_spam.batch_pause_min:.0f}s~{anti_spam.batch_pause_max:.0f}s)" if anti_spam.batch_pause_enabled else ""
        anti_spam_text = f"""
🛡️ *MOTOR ANTI-SPAM:*
⚡ Perfil: {label}
⏱️ Faixa de Delay: {anti_spam.min_delay:.1f}s ~ {anti_spam.max_delay:.1f}s (Jitter Ativo){pause_txt}
"""

    return f"""📊 *STATUS DO SISTEMA*

🤖 *UserBot:* {userbot_status}
🔄 *Aprovações Ativas:* {active_approvals_count} canais
⚡ *Tarefas em Background:* {background_tasks_count}
{anti_spam_text}
⚙️ *CONFIGURAÇÕES:*
⏱️ Delay médio: {current_delay}s

📈 *ESTATÍSTICAS:*
✅ Total de Aprovações: {stats.get('total_approvals', 0)}
📋 Comandos Executados: {stats.get('total_commands', 0)}
📢 Canais Salvos: {stats.get('channels_managed', 0)}

⏰ {now_str}"""


def format_channels_list(saved_channels: Dict[str, Dict[str, Any]], active_channels: List[int]) -> str:
    if not saved_channels:
        return (
            "📋 *NENHUM CANAL SALVO*\n\n"
            "Use `/add_canal ID` para adicionar canais\n\n"
            "📝 Exemplo: `/add_canal -1001234567890`"
        )

    text = "📋 *MEUS CANAIS SALVOS*\n\n"
    for str_id, info in saved_channels.items():
        cid = int(str_id)
        if cid in active_channels:
            status = "⚡ Aprovando..."
        else:
            status = "🔴 Parado"

        text += f"📢 {info.get('name', 'Sem Nome')}\n"
        text += f"🆔 ID: `{info.get('id', str_id)}`\n"
        text += f"🔄 Status: {status}\n\n"

    text += f"📊 Total: {len(saved_channels)} canais"
    return text


def format_pending_requests(channel_name: str, channel_id: int, requests: List[JoinRequest]) -> str:
    if not requests:
        return (
            f"📋 *RESULTADO - VERIFICAÇÃO*\n\n"
            f"🎯 {channel_name}\n"
            f"🆔 ID: `{channel_id}`\n"
            f"📊 *0 pedidos pendentes*\n\n"
            f"⚠️ Nenhum pedido encontrado!"
        )

    text = f"""📋 *{len(requests)} PEDIDOS ENCONTRADOS*

🎯 *Canal:* {channel_name}
🆔 *ID:* `{channel_id}`

👥 *Primeiros 10:*"""

    for i, req in enumerate(requests[:10], 1):
        username = f"@{req.username}" if req.username else "Sem @"
        date_str = req.date.strftime("%d/%m %H:%M") if req.date else ""
        text += f"\n{i}. {req.user_name}\n   🆔 {req.user_id} | {date_str}"

    if len(requests) > 10:
        text += f"\n\n... e mais {len(requests) - 10} pedidos"

    text += f"\n\n🚀 Use `/aprovar {channel_id}` para aprovar todos!"
    return text


def format_approval_confirmation(channel_name: str, channel_id: int, requests_count: int) -> str:
    return f"""🚀 *CONFIRMAÇÃO DE APROVAÇÃO*

🎯 *Canal:* {channel_name}
🆔 *ID:* `{channel_id}`
👥 *Pedidos para aprovar:* {requests_count}

⚠️ Esta ação irá aprovar TODOS os pedidos verificados anteriormente em **BACKGROUND**.

🔥 **O BOT CONTINUARÁ RESPONDENDO** outros comandos durante a aprovação!

**RESPONDA COM:**
- Digite **SIM** para confirmar
- Digite **NAO** para cancelar"""


def format_progress(progress: Optional[ApprovalProgress], channel_id: int) -> str:
    if not progress:
        return (
            f"⚡ *APROVAÇÃO EM ANDAMENTO*\n\n"
            f"🎯 Canal ID: `{channel_id}`\n"
            f"🔄 *Status:* Iniciando...\n\n"
            f"💡 Use `/parar_aprovacao {channel_id}` para cancelar"
        )

    return f"""⚡ *APROVAÇÃO EM ANDAMENTO*

🎯 *Canal:* {progress.channel_name}
🆔 *ID:* `{channel_id}`

📊 *PROGRESSO:*
🔄 Rodadas: {progress.rounds}
✅ Aprovados: {progress.approved}
❌ Falhas: {progress.failed}
⏰ Iniciado: {progress.start_time}

🔥 Status: {progress.status}

💡 Use `/parar_aprovacao {channel_id}` para cancelar"""


def format_approval_result(channel_name: str, channel_id: int, result: ApprovalResult) -> str:
    now_str = datetime.now().strftime("%H:%M:%S")
    return f"""🎉 *APROVAÇÃO CONCLUÍDA!*

🎯 *Canal:* {channel_name}
🆔 *ID:* `{channel_id}`

📊 *RESULTADO FINAL:*
🔄 Rodadas: {result.rounds}
✅ Aprovados: {result.approved}
❌ Falhas: {result.failed}

💬 {result.message}

⏰ Finalizada: {now_str}

🔥 O bot continuou respondendo outros comandos durante todo o processo!"""


def format_delay_info(current_delay: float, anti_spam: Optional[AntiSpamSettings] = None) -> str:
    profile_info = ""
    if anti_spam:
        profile_info = f"""
🛡️ *STATUS ANTI-SPAM:*
⚡ Perfil Atual: *{anti_spam.mode.upper()}*
⏱️ Faixa Ativa: *{anti_spam.min_delay:.1f}s a {anti_spam.max_delay:.1f}s* (Jitter Randômico)
☕ Micro-pausa: *{'Ativa (a cada ' + str(anti_spam.batch_size) + ' membros)' if anti_spam.batch_pause_enabled else 'Desativada'}*
"""
    return f"""⏱️ *CONFIGURAÇÃO DE DELAY & ANTI-SPAM*
{profile_info}
💡 *O motor Anti-Spam protege sua conta variando os segundos entre aprovações para evitar padrões previsíveis que causam FloodWait no Telegram.*

🚀 *COMANDOS DISPONÍVEIS:*

1️⃣ *Perfis Prontos:*
• `/delay seguro` - 1.2s a 2.8s (🛡️ Padrão Recomendado)
• `/delay rapido` - 0.8s a 1.5s (⚡ Mais rápido)
• `/delay furtivo` - 2.5s a 5.0s (🐢 Ultra-seguro / Stealth)

2️⃣ *Faixa Personalizada (Mínimo e Máximo):*
• `/delay 1.0 3.0` - Varia entre 1.0s e 3.0s

3️⃣ *Valor Médio Simples:*
• `/delay 2` - Média de 2s com variação automática (1.5s ~ 2.7s)"""


def format_recent_logs(logs: List[LogEntry]) -> str:
    if not logs:
        return "📋 Nenhum log registrado no momento."

    text = "📋 *LOGS RECENTES*\n\n"
    level_emojis = {"INFO": "ℹ️", "ERROR": "❌", "WARNING": "⚠️"}
    for log in logs:
        try:
            timestamp = datetime.fromisoformat(log.timestamp).strftime("%H:%M:%S")
        except Exception:
            timestamp = log.timestamp
        emoji = level_emojis.get(log.level, "📝")
        text += f"{emoji} `{timestamp}` {log.message}\n"
    return text
