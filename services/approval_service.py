"""
Serviço de Orquestração de Aprovações - Clean Architecture (Application Layer)
Gerencia a execução assíncrona de aprovações em background, rastreamento de progresso e cancelamento.
"""

import asyncio
import logging
from typing import Dict, Tuple, Optional, Callable, Awaitable
from core.entities import ApprovalResult
from core.interfaces import IUserBotGateway, IStorageRepository, ILogRepository
from core.exceptions import ApprovalCancelledError
from services.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


class ApprovalService:
    """Caso de uso: Execução e controle de aprovações em segundo plano."""

    def __init__(
        self,
        gateway: IUserBotGateway,
        storage: IStorageRepository,
        log_repository: ILogRepository,
        progress_tracker: ProgressTracker,
    ):
        self._gateway = gateway
        self._storage = storage
        self._logs = log_repository
        self._progress = progress_tracker
        self._running_tasks: Dict[int, Tuple[asyncio.Task, asyncio.Event]] = {}

    def is_channel_running(self, channel_id: int) -> bool:
        """Verifica se há aprovação em andamento para o canal."""
        return channel_id in self._running_tasks and not self._running_tasks[channel_id][0].done()

    def get_active_task_count(self) -> int:
        """Retorna o número de canais com tarefas em background ativas."""
        return len([cid for cid, (task, _) in self._running_tasks.items() if not task.done()])

    def cancel_approval(self, channel_id: int) -> bool:
        """Sinaliza parada cooperativa e cancela a tarefa em background."""
        if channel_id in self._running_tasks:
            task, stop_event = self._running_tasks[channel_id]
            stop_event.set()
            task.cancel()
            self._progress.stop_tracking(channel_id)
            self._logs.add_log(f"Aprovação do canal {channel_id} cancelada pelo usuário.", "WARNING")
            return True
        return False

    def start_background_approval(
        self,
        channel_id: int,
        channel_name: str,
        on_success: Optional[Callable[[ApprovalResult], Awaitable[None]]] = None,
        on_error: Optional[Callable[[Exception], Awaitable[None]]] = None,
        on_cancelled: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> bool:
        """Inicia uma tarefa assíncrona em segundo plano para aprovar os pedidos."""
        if self.is_channel_running(channel_id):
            return False

        stop_event = asyncio.Event()
        self._progress.start_tracking(channel_id, channel_name)

        task = asyncio.create_task(
            self._execute_approval_workflow(
                channel_id=channel_id,
                channel_name=channel_name,
                stop_event=stop_event,
                on_success=on_success,
                on_error=on_error,
                on_cancelled=on_cancelled,
            )
        )

        self._running_tasks[channel_id] = (task, stop_event)
        self._logs.add_log(f"Aprovação em background iniciada: {channel_name} ({channel_id})")
        return True

    async def _execute_approval_workflow(
        self,
        channel_id: int,
        channel_name: str,
        stop_event: asyncio.Event,
        on_success: Optional[Callable[[ApprovalResult], Awaitable[None]]],
        on_error: Optional[Callable[[Exception], Awaitable[None]]],
        on_cancelled: Optional[Callable[[], Awaitable[None]]],
    ):
        try:
            self._progress.update_progress(
                channel_id=channel_id,
                rounds=0,
                approved=0,
                failed=0,
                status="Conectando ao UserBot...",
            )

            if not await self._gateway.is_authenticated():
                connected = await self._gateway.connect()
                if not connected:
                    raise Exception("UserBot não autenticado ou desconectado.")

            self._progress.update_progress(
                channel_id=channel_id,
                rounds=0,
                approved=0,
                failed=0,
                status="Processando aprovações...",
            )

            delay = self._storage.get_delay()

            async def progress_cb(rounds: int, approved: int, failed: int):
                self._progress.update_progress(
                    channel_id=channel_id,
                    rounds=rounds,
                    approved=approved,
                    failed=failed,
                    status="Processando...",
                )

            result = await self._gateway.approve_all_channel_requests(
                channel_id=channel_id,
                approve_delay=delay,
                progress_callback=progress_cb,
                stop_event=stop_event,
            )

            # Atualizar estatísticas e limpar lista de verificação
            self._storage.increment_approvals_count(result.approved)
            self._storage.clear_last_checked(channel_id)
            self._progress.update_progress(
                channel_id=channel_id,
                rounds=result.rounds,
                approved=result.approved,
                failed=result.failed,
                status="Concluído!",
            )

            self._logs.add_log(
                f"Aprovação concluída no canal {channel_name}: {result.approved} aprovados, {result.failed} falhas."
            )

            if on_success:
                await on_success(result)

        except (asyncio.CancelledError, ApprovalCancelledError):
            logger.info(f"Tarefa de aprovação cancelada para o canal {channel_id}.")
            if on_cancelled:
                await on_cancelled()

        except Exception as e:
            logger.error(f"Erro na execução da aprovação para o canal {channel_id}: {e}", exc_info=True)
            self._logs.add_log(f"Erro na aprovação do canal {channel_id}: {e}", "ERROR")
            if on_error:
                await on_error(e)

        finally:
            self._running_tasks.pop(channel_id, None)
            self._progress.stop_tracking(channel_id)
