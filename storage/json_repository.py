"""
Repositório JSON Seguro - Clean Architecture (Infrastructure/Storage)
Gerencia a persistência de configurações, canais cadastrados e estatísticas com thread-lock.
"""

import json
import os
import threading
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class JsonStorageRepository:
    """Implementação segura de IStorageRepository usando arquivo JSON."""

    def __init__(self, config_filepath: str = "bot_config.json", default_delay: float = 1.0):
        self._filepath = config_filepath
        self._default_delay = default_delay
        self._lock = threading.Lock()
        self._data = self._load()

    def _get_default_schema(self) -> Dict[str, Any]:
        return {
            "saved_channels": {},
            "last_checked": {},
            "settings": {
                "approve_delay": self._default_delay,
                "log_level": "INFO",
            },
            "statistics": {
                "total_commands": 0,
                "total_approvals": 0,
                "channels_managed": 0,
            },
        }

    def _load(self) -> Dict[str, Any]:
        default = self._get_default_schema()
        if os.path.exists(self._filepath):
            try:
                with open(self._filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # Garantir que todas as seções essenciais existam
                for k, v in default.items():
                    if k not in loaded:
                        loaded[k] = v
                    elif isinstance(v, dict):
                        for sub_k, sub_v in v.items():
                            if sub_k not in loaded[k]:
                                loaded[k][sub_k] = sub_v
                return loaded
            except Exception as e:
                logger.error(f"Erro ao carregar {self._filepath}: {e}")
        return default

    def _save(self) -> None:
        try:
            temp_filepath = f"{self._filepath}.tmp"
            with open(temp_filepath, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            os.replace(temp_filepath, self._filepath)
        except Exception as e:
            logger.error(f"Erro ao salvar {self._filepath}: {e}")

    def get_delay(self) -> float:
        with self._lock:
            return float(self._data["settings"].get("approve_delay", self._default_delay))

    def set_delay(self, delay: float) -> None:
        with self._lock:
            self._data["settings"]["approve_delay"] = max(0.0, float(delay))
            self._save()

    def get_saved_channels(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._data.get("saved_channels", {}))

    def add_saved_channel(self, channel_id: int, name: str) -> None:
        with self._lock:
            if "saved_channels" not in self._data:
                self._data["saved_channels"] = {}
            self._data["saved_channels"][str(channel_id)] = {
                "id": channel_id,
                "name": name,
            }
            self._data["statistics"]["channels_managed"] = len(self._data["saved_channels"])
            self._save()

    def remove_saved_channel(self, channel_id: int) -> bool:
        with self._lock:
            str_id = str(channel_id)
            if "saved_channels" in self._data and str_id in self._data["saved_channels"]:
                del self._data["saved_channels"][str_id]
                self._data["statistics"]["channels_managed"] = len(self._data["saved_channels"])
                self._save()
                return True
            return False

    def get_last_checked(self, channel_id: int) -> List[int]:
        with self._lock:
            str_id = str(channel_id)
            return list(self._data.get("last_checked", {}).get(str_id, []))

    def set_last_checked(self, channel_id: int, user_ids: List[int]) -> None:
        with self._lock:
            if "last_checked" not in self._data:
                self._data["last_checked"] = {}
            self._data["last_checked"][str(channel_id)] = list(user_ids)
            self._save()

    def clear_last_checked(self, channel_id: int) -> None:
        with self._lock:
            str_id = str(channel_id)
            if "last_checked" in self._data and str_id in self._data["last_checked"]:
                del self._data["last_checked"][str_id]
                self._save()

    def increment_commands_count(self) -> None:
        with self._lock:
            self._data["statistics"]["total_commands"] += 1
            self._save()

    def increment_approvals_count(self, count: int) -> None:
        with self._lock:
            self._data["statistics"]["total_approvals"] += max(0, count)
            self._save()

    def get_statistics(self) -> Dict[str, int]:
        with self._lock:
            stats = dict(self._data.get("statistics", {}))
            stats["channels_managed"] = len(self._data.get("saved_channels", {}))
            return stats
