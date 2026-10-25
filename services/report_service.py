"""
Serviço de Geração de Relatórios e Planilhas - Clean Architecture (Application Layer)
Gera relatórios de leads fatiados a cada 100 pessoas em formato CSV compatível com Excel (UTF-8-SIG).
"""

import csv
import io
import re
from typing import List, Tuple
from core.entities import JoinRequest


class ReportService:
    """Caso de uso: Geração de planilhas/relatórios particionados de leads."""

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitiza o nome do canal para uso em arquivos."""
        sanitized = re.sub(r"[^\w\-]", "_", name)
        sanitized = re.sub(r"_+", "_", sanitized).strip("_")
        return sanitized or "canal"

    def generate_csv_batches(
        self,
        requests: List[JoinRequest],
        channel_title: str = "canal",
        batch_size: int = 100,
    ) -> List[Tuple[str, bytes]]:
        """
        Particiona a lista de solicitações em lotes de 'batch_size' (padrão 100)
        e gera arquivos CSV com codificação UTF-8-SIG (compatível com Excel / Google Sheets).

        Retorna uma lista de tuplas contendo: (nome_do_arquivo, conteudo_em_bytes)
        """
        if not requests:
            return []

        safe_title = self._sanitize_filename(channel_title)
        batches: List[Tuple[str, bytes]] = []
        total = len(requests)

        for i in range(0, total, batch_size):
            chunk = requests[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            filename = f"leads_{safe_title}_lote_{batch_num}_{len(chunk)}membros.csv"

            output = io.StringIO()
            writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

            # Cabeçalho da planilha
            writer.writerow(
                [
                    "ID do Usuário",
                    "Nome Completo",
                    "Username (@)",
                    "Link de Convite Utilizado",
                    "Título / Campanha do Link",
                    "Data e Hora da Solicitação",
                    "É Telegram Premium?",
                    "Bio / Mensagem do Pedido",
                ]
            )

            for req in chunk:
                # Formatar data de entrada
                if req.date:
                    date_str = req.date.strftime("%d/%m/%Y %H:%M:%S")
                else:
                    date_str = "-"

                username_str = f"@{req.username}" if req.username else "-"
                invite_link_str = req.invite_link if req.invite_link else "Link Padrão / Direto"
                invite_title_str = req.invite_title if req.invite_title else "-"
                is_premium_str = "Sim" if req.is_premium else "Não"
                about_str = req.about.strip() if req.about else "-"

                writer.writerow(
                    [
                        str(req.user_id),
                        req.user_name,
                        username_str,
                        invite_link_str,
                        invite_title_str,
                        date_str,
                        is_premium_str,
                        about_str,
                    ]
                )

            # Codificar com UTF-8-SIG (com BOM para acentos corretos no Excel)
            csv_bytes = output.getvalue().encode("utf-8-sig")
            batches.append((filename, csv_bytes))

        return batches
