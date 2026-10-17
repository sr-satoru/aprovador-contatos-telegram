"""
Middlewares e Decorators de Segurança do Bot
"""

from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes


def check_authorized(func):
    """
    Decorator para verificar se o usuário que enviou o comando está autorizado.
    Lê a lista de usuários autorizados a partir de context.bot_data['authorized_users'].
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        authorized_users = context.bot_data.get("authorized_users", [])
        if authorized_users and user.id not in authorized_users:
            if update.message:
                await update.message.reply_text("❌ Você não tem permissão para usar este bot!")
            elif update.callback_query:
                await update.callback_query.answer("❌ Você não tem permissão para usar este bot!", show_alert=True)
            return

        return await func(update, context, *args, **kwargs)

    return wrapper
