"""
Entidades de Domínio - Clean Architecture
Modelos puros sem dependência de bibliotecas de terceiros (Telethon, PTB, etc.).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class ChannelInfo:
    """Informações representativas de um canal ou supergrupo."""
    id: int
    title: str
    username: Optional[str] = None
    participants_count: Optional[int] = None
    is_admin: bool = False
    can_invite: bool = False
    is_broadcast: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "username": self.username,
            "participants_count": self.participants_count,
            "is_admin": self.is_admin,
            "can_invite": self.can_invite,
            "is_broadcast": self.is_broadcast,
        }


@dataclass(frozen=True)
class JoinRequest:
    """Dados de uma solicitação de entrada (Join Request) em um canal."""
    user_id: int
    user_name: str
    username: Optional[str] = None
    date: Optional[datetime] = None
    about: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "username": self.username,
            "date": self.date.isoformat() if self.date else None,
            "about": self.about,
        }


@dataclass
class ApprovalProgress:
    """Progresso em tempo real da aprovação de pedidos de um canal."""
    channel_id: int
    channel_name: str
    start_time: str
    status: str
    rounds: int = 0
    approved: int = 0
    failed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "start_time": self.start_time,
            "status": self.status,
            "rounds": self.rounds,
            "approved": self.approved,
            "failed": self.failed,
        }


@dataclass(frozen=True)
class ApprovalResult:
    """Resultado consolidado de uma operação de aprovação."""
    rounds: int
    approved: int
    failed: int
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": f"{self.rounds} rodadas",
            "approved": f"{self.approved} aprovados",
            "failed": self.failed,
            "message": self.message,
        }


@dataclass(frozen=True)
class LogEntry:
    """Entrada individual de log do sistema."""
    timestamp: str
    level: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
        }
