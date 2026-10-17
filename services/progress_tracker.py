"""
Rastreador de Progresso em Memória - Clean Architecture (Application Layer)
Mantém o estado em tempo real das aprovações em background para consultas rápidas.
"""

import threading
from datetime import datetime
from typing import Dict, Optional
from core.entities import ApprovalProgress


class ProgressTracker:
    """Gerencia o progresso das tarefas de aprovação ativas em memória."""

    def __init__(self):
        self._lock = threading.Lock()
        self._active_progress: Dict[int, ApprovalProgress] = {}

    def start_tracking(self, channel_id: int, channel_name: str) -> ApprovalProgress:
        with self._lock:
            progress = ApprovalProgress(
                channel_id=channel_id,
                channel_name=channel_name,
                start_time=datetime.now().strftime("%H:%M:%S"),
                status="Iniciando...",
                rounds=0,
                approved=0,
                failed=0,
            )
            self._active_progress[channel_id] = progress
            return progress

    def update_progress(
        self,
        channel_id: int,
        rounds: int,
        approved: int,
        failed: int,
        status: Optional[str] = None,
    ) -> None:
        with self._lock:
            if channel_id in self._active_progress:
                prog = self._active_progress[channel_id]
                prog.rounds = rounds
                prog.approved = approved
                prog.failed = failed
                if status:
                    prog.status = status

    def get_progress(self, channel_id: int) -> Optional[ApprovalProgress]:
        with self._lock:
            prog = self._active_progress.get(channel_id)
            if prog:
                # Retorna cópia para evitar mutações concorrentes externas
                return ApprovalProgress(
                    channel_id=prog.channel_id,
                    channel_name=prog.channel_name,
                    start_time=prog.start_time,
                    status=prog.status,
                    rounds=prog.rounds,
                    approved=prog.approved,
                    failed=prog.failed,
                )
            return None

    def is_active(self, channel_id: int) -> bool:
        with self._lock:
            return channel_id in self._active_progress

    def stop_tracking(self, channel_id: int) -> Optional[ApprovalProgress]:
        with self._lock:
            return self._active_progress.pop(channel_id, None)

    def get_all_active(self) -> Dict[int, ApprovalProgress]:
        with self._lock:
            return {k: self.get_progress(k) for k in self._active_progress}  # type: ignore
