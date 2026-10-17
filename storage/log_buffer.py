"""
Buffer de Logs - Clean Architecture (Infrastructure/Storage)
Gerencia o armazenamento circular de logs em memória e em arquivo JSON.
"""

import json
import os
import threading
import logging
from collections import deque
from datetime import datetime
from typing import List
from core.entities import LogEntry

logger = logging.getLogger(__name__)


class LogBufferRepository:
    """Implementação segura de ILogRepository."""

    def __init__(self, filepath: str = "bot_logs.json", max_memory_logs: int = 1000):
        self._filepath = filepath
        self._max_logs = max_memory_logs
        self._lock = threading.Lock()
        self._buffer: deque[LogEntry] = deque(maxlen=max_memory_logs)
        self._load_existing()

    def _load_existing(self) -> None:
        if os.path.exists(self._filepath):
            try:
                with open(self._filepath, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                    for item in entries[-self._max_logs:]:
                        self._buffer.append(
                            LogEntry(
                                timestamp=item.get("timestamp", datetime.now().isoformat()),
                                level=item.get("level", "INFO"),
                                message=item.get("message", ""),
                            )
                        )
            except Exception as e:
                logger.error(f"Erro ao carregar logs existentes de {self._filepath}: {e}")

    def add_log(self, message: str, level: str = "INFO") -> None:
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            message=message,
        )
        with self._lock:
            self._buffer.append(entry)
            try:
                raw_list = [e.to_dict() for e in self._buffer]
                temp_filepath = f"{self._filepath}.tmp"
                with open(temp_filepath, "w", encoding="utf-8") as f:
                    json.dump(raw_list, f, indent=2, ensure_ascii=False)
                os.replace(temp_filepath, self._filepath)
            except Exception as e:
                logger.error(f"Erro ao persistir logs em {self._filepath}: {e}")

    def get_recent_logs(self, limit: int = 8) -> List[LogEntry]:
        with self._lock:
            items = list(self._buffer)
            return items[-limit:]
