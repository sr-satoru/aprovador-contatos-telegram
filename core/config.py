"""
Gerenciamento de Configurações - Clean Architecture
Carregamento tipado a partir de variáveis de ambiente (.env) ou padrões seguros.
"""

import os
from dataclasses import dataclass
from typing import List

# Tentar importar python-dotenv se estiver disponível
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Se python-dotenv não estiver instalado, carregar manualmente do .env se existir
    if os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
        except Exception:
            pass


@dataclass(frozen=True)
class UserBotConfig:
    """Configurações específicas do UserBot (Telethon MTProto)."""
    api_id: int
    api_hash: str
    phone_number: str
    senha_2fa: str
    session_file: str = "conta.session"

    def is_configured(self) -> bool:
        """Verifica se as credenciais foram preenchidas."""
        return (
            self.api_id not in (0, 123456)
            and bool(self.api_hash)
            and self.api_hash != "SEU_API_HASH_AQUI"
            and bool(self.phone_number)
            and self.phone_number != "+5511999999999"
        )


@dataclass(frozen=True)
class BotConfig:
    """Configurações específicas do Bot Controlador (python-telegram-bot)."""
    token: str
    authorized_users: List[int]
    config_file: str = "bot_config.json"
    logs_file: str = "bot_logs.json"

    def is_configured(self) -> bool:
        """Verifica se o token e usuários foram preenchidos."""
        return bool(self.token) and self.token != "SEU_BOT_TOKEN_AQUI" and bool(self.authorized_users)


@dataclass(frozen=True)
class AppConfig:
    """Configurações globais consolidadas da aplicação."""
    userbot: UserBotConfig
    bot: BotConfig
    default_delay: float = 1.0


def _parse_authorized_users(raw_users: str) -> List[int]:
    """Converte string de IDs ('123, 456') ou lista para List[int]."""
    if not raw_users:
        return []
    users = []
    for part in raw_users.replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit():
            users.append(int(part))
    return users


def load_config() -> AppConfig:
    """
    Carrega todas as configurações do ambiente com validação e fallback seguro.
    """
    raw_api_id = os.getenv("API_ID", "123456")
    try:
        api_id = int(raw_api_id)
    except ValueError:
        api_id = 123456

    api_hash = os.getenv("API_HASH", "SEU_API_HASH_AQUI")
    phone_number = os.getenv("PHONE_NUMBER", "+5511999999999")
    senha_2fa = os.getenv("SENHA_2FA", "SUA_SENHA_2FA_AQUI")
    session_file = os.getenv("SESSION_FILE", "conta.session")

    bot_token = os.getenv("BOT_TOKEN", "SEU_BOT_TOKEN_AQUI")
    raw_auth_users = os.getenv("AUTHORIZED_USERS", "")
    authorized_users = _parse_authorized_users(raw_auth_users)
    config_file = os.getenv("CONFIG_FILE", "bot_config.json")
    logs_file = os.getenv("LOGS_FILE", "bot_logs.json")

    raw_delay = os.getenv("APPROVE_DELAY", "1.0")
    try:
        default_delay = float(raw_delay)
    except ValueError:
        default_delay = 1.0

    return AppConfig(
        userbot=UserBotConfig(
            api_id=api_id,
            api_hash=api_hash,
            phone_number=phone_number,
            senha_2fa=senha_2fa,
            session_file=session_file,
        ),
        bot=BotConfig(
            token=bot_token,
            authorized_users=authorized_users,
            config_file=config_file,
            logs_file=logs_file,
        ),
        default_delay=default_delay,
    )
