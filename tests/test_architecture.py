"""
Testes Automatizados - Clean Architecture & Unidade
Valida integridade do domínio, serviços, persistência, formatadores e separação de camadas.
"""

import os
import sys
import asyncio
import tempfile
import unittest
from datetime import datetime
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock

# Adicionar raiz ao sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.entities import ChannelInfo, JoinRequest, ApprovalProgress, ApprovalResult, LogEntry, AntiSpamSettings
from core.config import load_config, _parse_authorized_users, AppConfig, UserBotConfig, BotConfig
from storage.json_repository import JsonStorageRepository
from storage.log_buffer import LogBufferRepository
from services.progress_tracker import ProgressTracker
from services.channel_service import ChannelService
from services.approval_service import ApprovalService
from bot import formatters
from bot.middlewares import check_authorized


class MockUserBotGateway:
    """Mock do gateway Telethon para testes sem conexão real de rede."""

    def __init__(self):
        self.is_auth = True
        self.channel_to_return = ChannelInfo(
            id=12345,
            title="Canal de Teste",
            username="canalteste",
            participants_count=100,
            is_admin=True,
            can_invite=True,
        )
        self.requests_to_return = [
            JoinRequest(user_id=101, user_name="User 1", username="user1", date=datetime.now()),
            JoinRequest(user_id=102, user_name="User 2", username="user2", date=datetime.now()),
        ]

    async def is_authenticated(self) -> bool:
        return self.is_auth

    async def connect(self) -> bool:
        return self.is_auth

    async def disconnect(self) -> None:
        pass

    async def get_channel_info(self, channel_id: int | str) -> Optional[ChannelInfo]:
        return self.channel_to_return

    async def fetch_pending_requests(self, channel_id: int, limit: Optional[int] = None) -> List[JoinRequest]:
        return self.requests_to_return

    async def approve_all_channel_requests(
        self,
        channel_id: int,
        approve_delay: float = 1.0,
        anti_spam=None,
        progress_callback=None,
        stop_event=None,
    ) -> ApprovalResult:
        if stop_event and stop_event.is_set():
            raise asyncio.CancelledError()
        if progress_callback:
            try:
                await progress_callback(1, 2, 0, "Processando...")
            except TypeError:
                await progress_callback(1, 2, 0)
        return ApprovalResult(rounds=1, approved=2, failed=0, message="2 pedidos aprovados!")


class TestEntities(unittest.TestCase):
    def test_channel_info_serialization(self):
        ch = ChannelInfo(id=999, title="Teste", username="teste_bot", is_admin=True)
        d = ch.to_dict()
        self.assertEqual(d["id"], 999)
        self.assertEqual(d["title"], "Teste")
        self.assertTrue(d["is_admin"])

    def test_join_request_serialization(self):
        req = JoinRequest(user_id=555, user_name="Vanir", username="vanir_dev")
        d = req.to_dict()
        self.assertEqual(d["user_id"], 555)
        self.assertEqual(d["user_name"], "Vanir")

    def test_approval_progress_serialization(self):
        prog = ApprovalProgress(
            channel_id=123,
            channel_name="Canal",
            start_time="10:00:00",
            status="Processando",
            rounds=2,
            approved=15,
            failed=1,
        )
        d = prog.to_dict()
        self.assertEqual(d["channel_id"], 123)
        self.assertEqual(d["approved"], 15)

    def test_log_entry_serialization(self):
        entry = LogEntry(timestamp="2026-10-17T10:00:00", level="INFO", message="Teste")
        d = entry.to_dict()
        self.assertEqual(d["level"], "INFO")
        self.assertEqual(d["message"], "Teste")


class TestConfig(unittest.TestCase):
    def test_parse_authorized_users(self):
        raw = "123, 456; abc, 789"
        parsed = _parse_authorized_users(raw)
        self.assertEqual(parsed, [123, 456, 789])

    def test_default_config_load(self):
        config = load_config()
        self.assertIsInstance(config, AppConfig)
        self.assertIsInstance(config.userbot, UserBotConfig)
        self.assertIsInstance(config.bot, BotConfig)

    def test_is_configured(self):
        unconf_userbot = UserBotConfig(api_id=123456, api_hash="", phone_number="", senha_2fa="")
        self.assertFalse(unconf_userbot.is_configured())

        conf_userbot = UserBotConfig(api_id=98765, api_hash="hash123", phone_number="+5511999998888", senha_2fa="")
        self.assertTrue(conf_userbot.is_configured())

        unconf_bot = BotConfig(token="SEU_BOT_TOKEN_AQUI", authorized_users=[])
        self.assertFalse(unconf_bot.is_configured())

        conf_bot = BotConfig(token="123456:ABC-DEF", authorized_users=[12345])
        self.assertTrue(conf_bot.is_configured())


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "test_config.json")
        self.logs_path = os.path.join(self.temp_dir.name, "test_logs.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_json_storage_repository(self):
        repo = JsonStorageRepository(self.config_path, default_delay=1.5)

        # Delay
        self.assertEqual(repo.get_delay(), 1.5)
        repo.set_delay(2.0)
        self.assertEqual(repo.get_delay(), 2.0)

        # Canais
        repo.add_saved_channel(1234, "Canal Alfa")
        channels = repo.get_saved_channels()
        self.assertIn("1234", channels)
        self.assertEqual(channels["1234"]["name"], "Canal Alfa")

        # Remoção de canais
        removed = repo.remove_saved_channel(1234)
        self.assertTrue(removed)
        self.assertNotIn("1234", repo.get_saved_channels())

        # Last Checked
        repo.set_last_checked(5678, [10, 20, 30])
        self.assertEqual(repo.get_last_checked(5678), [10, 20, 30])
        repo.clear_last_checked(5678)
        self.assertEqual(repo.get_last_checked(5678), [])

        # Estatísticas
        repo.increment_commands_count()
        repo.increment_approvals_count(5)
        stats = repo.get_statistics()
        self.assertEqual(stats["total_commands"], 1)
        self.assertEqual(stats["total_approvals"], 5)

    def test_log_buffer_repository(self):
        repo = LogBufferRepository(self.logs_path, max_memory_logs=5)
        for i in range(10):
            repo.add_log(f"Mensagem {i}", "INFO")

        recent = repo.get_recent_logs(3)
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[-1].message, "Mensagem 9")


class TestServices(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "test_config.json")
        self.logs_path = os.path.join(self.temp_dir.name, "test_logs.json")
        self.storage = JsonStorageRepository(self.config_path, default_delay=1.0)
        self.logs = LogBufferRepository(self.logs_path)
        self.gateway = MockUserBotGateway()
        self.tracker = ProgressTracker()

    def tearDown(self):
        self.temp_dir.cleanup()

    async def test_channel_service(self):
        service = ChannelService(self.gateway, self.storage)
        info = await service.add_channel(12345)
        self.assertEqual(info.title, "Canal de Teste")

        requests = await service.check_channel_requests(12345)
        self.assertEqual(len(requests), 2)
        self.assertEqual(service.get_pending_user_ids(12345), [101, 102])

        service.clear_pending_user_ids(12345)
        self.assertEqual(service.get_pending_user_ids(12345), [])

    async def test_approval_service(self):
        service = ApprovalService(self.gateway, self.storage, self.logs, self.tracker)

        finished_event = asyncio.Event()
        result_holder = []

        async def on_success(res: ApprovalResult):
            result_holder.append(res)
            finished_event.set()

        started = service.start_background_approval(
            channel_id=12345,
            channel_name="Canal de Teste",
            on_success=on_success,
        )
        self.assertTrue(started)

        await asyncio.wait_for(finished_event.wait(), timeout=5.0)
        self.assertEqual(len(result_holder), 1)
        self.assertEqual(result_holder[0].approved, 2)
        self.assertEqual(self.storage.get_statistics()["total_approvals"], 2)


class TestFormatters(unittest.TestCase):
    def test_format_welcome(self):
        text = formatters.format_welcome("Vanir")
        self.assertIn("Vanir", text)
        self.assertIn("/canais", text)

    def test_format_status(self):
        text = formatters.format_status(
            userbot_connected=True,
            active_approvals_count=2,
            background_tasks_count=2,
            current_delay=1.0,
            stats={"total_approvals": 100, "total_commands": 50, "channels_managed": 3},
        )
        self.assertIn("Conectado", text)
        self.assertIn("100", text)

    def test_format_channels_list(self):
        channels = {"123": {"id": 123, "name": "Canal 1"}}
        text = formatters.format_channels_list(channels, [123])
        self.assertIn("Canal 1", text)
        self.assertIn("Aprovando...", text)


class TestMiddlewares(unittest.IsolatedAsyncioTestCase):
    async def test_check_authorized_blocks_unauthorized_user(self):
        mock_handler = AsyncMock()
        decorated = check_authorized(mock_handler)

        update = MagicMock()
        update.effective_user.id = 999999
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.bot_data = {"authorized_users": [111111, 222222]}

        await decorated(update, context)
        mock_handler.assert_not_called()
        update.message.reply_text.assert_called_once()

    async def test_check_authorized_allows_authorized_user(self):
        mock_handler = AsyncMock()
        decorated = check_authorized(mock_handler)

        update = MagicMock()
        update.effective_user.id = 111111
        context = MagicMock()
        context.bot_data = {"authorized_users": [111111, 222222]}

        await decorated(update, context)
        mock_handler.assert_called_once_with(update, context)


class TestArchitecturalIsolation(unittest.TestCase):
    """Garante que as camadas não importam módulos indevidos."""

    def test_userbot_does_not_import_telegram(self):
        userbot_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "userbot"))
        for root, _, files in os.walk(userbot_dir):
            for file in files:
                if file.endswith(".py"):
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        content = f.read()
                        self.assertNotIn(
                            "from telegram",
                            content,
                            f"Violação de Arquitetura: {file} em userbot/ não deve importar telegram!",
                        )
                        self.assertNotIn(
                            "import telegram",
                            content,
                            f"Violação de Arquitetura: {file} em userbot/ não deve importar telegram!",
                        )

    def test_bot_does_not_import_telethon(self):
        bot_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bot"))
        for root, _, files in os.walk(bot_dir):
            for file in files:
                if file.endswith(".py"):
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        content = f.read()
                        self.assertNotIn(
                            "from telethon",
                            content,
                            f"Violação de Arquitetura: {file} em bot/ não deve importar telethon!",
                        )
                        self.assertNotIn(
                            "import telethon",
                            content,
                            f"Violação de Arquitetura: {file} em bot/ não deve importar telethon!",
                        )


class TestAntiSpam(unittest.IsolatedAsyncioTestCase):
    """Testes unitários do motor Anti-Spam com delays randômicos e perfis."""

    def test_presets_creation(self):
        fast = AntiSpamSettings.create_preset("fast")
        self.assertEqual(fast.mode, "fast")
        self.assertEqual(fast.min_delay, 0.8)
        self.assertEqual(fast.max_delay, 1.5)

        balanced = AntiSpamSettings.create_preset("balanced")
        self.assertEqual(balanced.mode, "balanced")
        self.assertEqual(balanced.min_delay, 1.2)
        self.assertEqual(balanced.max_delay, 2.8)

        stealth = AntiSpamSettings.create_preset("stealth")
        self.assertEqual(stealth.mode, "stealth")
        self.assertEqual(stealth.min_delay, 2.5)
        self.assertEqual(stealth.max_delay, 5.0)

    def test_random_delay_within_bounds(self):
        settings = AntiSpamSettings(min_delay=1.0, max_delay=3.0)
        for _ in range(50):
            d = settings.get_approval_delay()
            self.assertGreaterEqual(d, 1.0)
            self.assertLessEqual(d, 3.0)

    def test_batch_pause_within_bounds(self):
        settings = AntiSpamSettings(batch_pause_min=4.0, batch_pause_max=8.0)
        for _ in range(50):
            p = settings.get_batch_pause()
            self.assertGreaterEqual(p, 4.0)
            self.assertLessEqual(p, 8.0)

    def test_storage_anti_spam_integration(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "test_config.json")
            repo = JsonStorageRepository(path)

            # Default profile is balanced
            anti_spam = repo.get_anti_spam_settings()
            self.assertEqual(anti_spam.mode, "balanced")
            self.assertEqual(anti_spam.min_delay, 1.2)
            self.assertEqual(anti_spam.max_delay, 2.8)

            # Switch to fast profile
            repo.set_anti_spam_profile("fast")
            anti_spam = repo.get_anti_spam_settings()
            self.assertEqual(anti_spam.mode, "fast")
            self.assertEqual(anti_spam.min_delay, 0.8)
            self.assertEqual(anti_spam.max_delay, 1.5)

            # Switch to stealth profile
            repo.set_anti_spam_profile("stealth")
            anti_spam = repo.get_anti_spam_settings()
            self.assertEqual(anti_spam.mode, "stealth")
            self.assertEqual(anti_spam.min_delay, 2.5)

            # Custom range
            repo.set_anti_spam_range(1.5, 3.5)
            anti_spam = repo.get_anti_spam_settings()
            self.assertEqual(anti_spam.mode, "custom")
            self.assertEqual(anti_spam.min_delay, 1.5)
            self.assertEqual(anti_spam.max_delay, 3.5)

            # Single value delay automatically creates jitter
            repo.set_delay(2.0)
            anti_spam = repo.get_anti_spam_settings()
            self.assertEqual(anti_spam.min_delay, 1.5)
            self.assertEqual(anti_spam.max_delay, 2.7)

    async def test_delay_command_bot_handler(self):
        from bot.handlers.admin import delay_command

        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = os.path.join(tmp_dir, "config.json")
            logs_path = os.path.join(tmp_dir, "logs.json")
            storage = JsonStorageRepository(config_path)
            logs = LogBufferRepository(logs_path)

            update = MagicMock()
            update.effective_user.id = 12345
            update.message.reply_text = AsyncMock()

            context = MagicMock()
            context.bot_data = {
                "authorized_users": [12345],
                "storage": storage,
                "logs": logs,
            }

            # 1. /delay rapido
            context.args = ["rapido"]
            await delay_command(update, context)
            self.assertEqual(storage.get_anti_spam_settings().mode, "fast")
            update.message.reply_text.assert_called()

            # 2. /delay 1.0 2.5
            context.args = ["1.0", "2.5"]
            await delay_command(update, context)
            settings = storage.get_anti_spam_settings()
            self.assertEqual(settings.min_delay, 1.0)
            self.assertEqual(settings.max_delay, 2.5)


if __name__ == "__main__":
    unittest.main()
