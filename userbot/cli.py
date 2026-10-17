"""
CLI Interativo do UserBot - Terminal
Permite executar verificações e aprovações diretamente pelo terminal quando desejado.
"""

import asyncio
import logging
from core.config import load_config
from storage.json_repository import JsonStorageRepository
from userbot.client import TelethonClientManager
from userbot.authenticator import UserBotAuthenticator
from userbot.gateway import TelethonUserBotGateway

logger = logging.getLogger(__name__)


class UserBotCLI:
    """Menu interativo para operação via console."""

    def __init__(self):
        self.config = load_config()
        self.storage = JsonStorageRepository(
            self.config.bot.config_file, self.config.default_delay
        )
        self.client_manager = TelethonClientManager(self.config.userbot)
        self.authenticator = UserBotAuthenticator(self.config.userbot, self.client_manager)
        self.gateway = TelethonUserBotGateway(self.client_manager)

    async def run(self):
        print("\n" + "=" * 60)
        print("🚀 TELETHON USERBOT - INTERFACE DE TERMINAL")
        print("=" * 60)

        # Autenticar se necessário
        user_info = await self.authenticator.authenticate_interactive()
        if not user_info:
            print("❌ Não foi possível autenticar o UserBot. Encerrando.")
            return

        while True:
            delay = self.storage.get_delay()
            stats = self.storage.get_statistics()
            print("\n" + "-" * 50)
            print(f"👤 Usuário: {user_info['name']} (ID: {user_info['id']})")
            print(f"📊 Total Aprovado: {stats.get('total_approvals', 0)}")
            print(f"⏱️ Delay Atual: {delay}s")
            print("-" * 50)
            print("1. 🔍 Verificar pedidos pendentes de um canal")
            print("2. 🔥 Aprovar todos os pedidos de um canal")
            print("3. 📢 Ver informações de um canal")
            print("4. ⏱️ Configurar delay entre aprovações")
            print("5. ❌ Sair")

            try:
                choice = input("\n➤ Escolha uma opção (1-5): ").strip()
                if choice == "1":
                    await self._menu_check_requests()
                elif choice == "2":
                    await self._menu_approve_requests()
                elif choice == "3":
                    await self._menu_channel_info()
                elif choice == "4":
                    self._menu_configure_delay()
                elif choice == "5":
                    print("\n👋 Encerrando CLI do UserBot...")
                    break
                else:
                    print("❌ Opção inválida!")
            except (KeyboardInterrupt, EOFError):
                print("\n\n👋 Encerrando...")
                break
            except Exception as e:
                print(f"❌ Erro: {e}")

        await self.gateway.disconnect()

    async def _menu_check_requests(self):
        channel_input = input("\n📋 Digite o ID ou @username do canal: ").strip()
        if not channel_input:
            return
        try:
            channel_id = int(channel_input) if channel_input.lstrip("-").isdigit() else channel_input
            print("🔍 Buscando pedidos...")
            requests = await self.gateway.fetch_pending_requests(channel_id)
            print(f"\n📊 Total de pedidos pendentes: {len(requests)}")
            for i, r in enumerate(requests[:10], 1):
                username_str = f"@{r.username}" if r.username else "Sem @"
                date_str = r.date.strftime("%d/%m %H:%M") if r.date else ""
                print(f"  {i}. {r.user_name} (ID: {r.user_id}) [{username_str}] {date_str}")
            if len(requests) > 10:
                print(f"  ... e mais {len(requests) - 10} pedidos.")
        except Exception as e:
            print(f"❌ Erro ao buscar pedidos: {e}")

    async def _menu_approve_requests(self):
        channel_input = input("\n📋 Digite o ID ou @username do canal: ").strip()
        if not channel_input:
            return
        confirm = input("⚠️ Deseja realmente aprovar todos os pedidos? (s/N): ").strip().lower()
        if confirm != "s":
            print("Operação cancelada.")
            return

        try:
            channel_id = int(channel_input) if channel_input.lstrip("-").isdigit() else channel_input
            delay = self.storage.get_delay()
            print(f"🚀 Iniciando aprovação contínua (delay: {delay}s)...")

            async def progress_cb(rounds: int, approved: int, failed: int):
                if approved % 10 == 0:
                    print(f"⚡ Progresso: {approved} aprovados | {failed} falhas (Rodada {rounds})")

            result = await self.gateway.approve_all_channel_requests(
                channel_id=channel_id,
                approve_delay=delay,
                progress_callback=progress_cb,
            )
            print(f"\n🎉 {result.message}")
            self.storage.increment_approvals_count(result.approved)
        except Exception as e:
            print(f"❌ Erro durante aprovação: {e}")

    async def _menu_channel_info(self):
        channel_input = input("\n📋 Digite o ID ou @username do canal: ").strip()
        if not channel_input:
            return
        try:
            info = await self.gateway.get_channel_info(channel_input)
            if info:
                print(f"\n📢 Título: {info.title}")
                print(f"🆔 ID: {info.id}")
                print(f"👥 Membros: {info.participants_count or 'N/A'}")
                print(f"👑 É Administrador: {'Sim' if info.is_admin else 'Não'}")
            else:
                print("❌ Informações não disponíveis.")
        except Exception as e:
            print(f"❌ Erro: {e}")

    def _menu_configure_delay(self):
        current = self.storage.get_delay()
        print(f"\n⏱️ Delay atual: {current} segundos")
        new_val = input("Digite o novo delay em segundos (ex: 1.0, 0.5): ").strip()
        try:
            delay = float(new_val)
            if delay < 0:
                print("❌ O delay não pode ser negativo!")
                return
            self.storage.set_delay(delay)
            print(f"✅ Delay configurado para {delay}s com sucesso!")
        except ValueError:
            print("❌ Valor inválido.")


async def main():
    cli = UserBotCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
