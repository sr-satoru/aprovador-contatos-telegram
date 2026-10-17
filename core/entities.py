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


@dataclass
class AntiSpamSettings:
    """Configurações e parâmetros do motor Anti-Spam com delays randômicos."""
    mode: str = "balanced"  # 'fast', 'balanced', 'stealth', 'custom'
    min_delay: float = 1.2
    max_delay: float = 2.8
    batch_pause_enabled: bool = True
    batch_size: int = 20
    batch_pause_min: float = 4.0
    batch_pause_max: float = 8.0
    inter_round_min: float = 2.0
    inter_round_max: float = 4.5

    def get_approval_delay(self) -> float:
        """Gera um delay randômico realista entre aprovações individuais."""
        import random
        low = min(self.min_delay, self.max_delay)
        high = max(self.min_delay, self.max_delay)
        return random.uniform(max(0.1, low), max(0.1, high))

    def get_batch_pause(self) -> float:
        """Gera a duração randômica da micro-pausa de lote."""
        import random
        low = min(self.batch_pause_min, self.batch_pause_max)
        high = max(self.batch_pause_min, self.batch_pause_max)
        return random.uniform(low, high)

    def get_round_delay(self) -> float:
        """Gera o delay randômico entre rodadas de paginação do MTProto."""
        import random
        low = min(self.inter_round_min, self.inter_round_max)
        high = max(self.inter_round_min, self.inter_round_max)
        return random.uniform(low, high)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "min_delay": self.min_delay,
            "max_delay": self.max_delay,
            "batch_pause_enabled": self.batch_pause_enabled,
            "batch_size": self.batch_size,
            "batch_pause_min": self.batch_pause_min,
            "batch_pause_max": self.batch_pause_max,
            "inter_round_min": self.inter_round_min,
            "inter_round_max": self.inter_round_max,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AntiSpamSettings":
        if not data:
            return cls.create_preset("balanced")
        return cls(
            mode=data.get("mode", "balanced"),
            min_delay=float(data.get("min_delay", 1.2)),
            max_delay=float(data.get("max_delay", 2.8)),
            batch_pause_enabled=bool(data.get("batch_pause_enabled", True)),
            batch_size=int(data.get("batch_size", 20)),
            batch_pause_min=float(data.get("batch_pause_min", 4.0)),
            batch_pause_max=float(data.get("batch_pause_max", 8.0)),
            inter_round_min=float(data.get("inter_round_min", 2.0)),
            inter_round_max=float(data.get("inter_round_max", 4.5)),
        )

    @classmethod
    def create_preset(cls, profile: str) -> "AntiSpamSettings":
        """Cria uma instância pré-configurada a partir de um perfil nomeado."""
        profile_clean = profile.lower().strip()
        if profile_clean in ("fast", "rapido", "rápido"):
            return cls(
                mode="fast",
                min_delay=0.8,
                max_delay=1.5,
                batch_pause_enabled=True,
                batch_size=30,
                batch_pause_min=3.0,
                batch_pause_max=5.0,
                inter_round_min=1.5,
                inter_round_max=3.0,
            )
        elif profile_clean in ("stealth", "furtivo"):
            return cls(
                mode="stealth",
                min_delay=2.5,
                max_delay=5.0,
                batch_pause_enabled=True,
                batch_size=15,
                batch_pause_min=6.0,
                batch_pause_max=12.0,
                inter_round_min=3.0,
                inter_round_max=6.0,
            )
        else:  # 'balanced' / 'seguro' (Padrão)
            return cls(
                mode="balanced",
                min_delay=1.2,
                max_delay=2.8,
                batch_pause_enabled=True,
                batch_size=20,
                batch_pause_min=4.0,
                batch_pause_max=8.0,
                inter_round_min=2.0,
                inter_round_max=4.5,
            )

