"""
Forwarding Table - Tabela de encaminhamento tipo switch learning.

Cada dispositivo aprende por qual link deve enviar mensagens para cada NID:
- Quando recebe mensagem do NID X pelo link Y → memoriza (X → Y)
- Quando precisa enviar para X → consulta tabela e envia por Y
"""

from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from threading import Lock

from common.utils.nid import NID
from common.utils.logger import get_logger

logger = get_logger("forwarding_table")


class ForwardingEntry:
    """
    Entrada na tabela de forwarding.

    Attributes:
        nid: Network Identifier do destino
        link: Identificador do link BLE (pode ser MAC address, connection handle, etc.)
        timestamp: Quando esta entrada foi aprendida/atualizada
        packet_count: Número de pacotes encaminhados para este destino
    """

    def __init__(self, nid: NID, link: Any):
        """
        Cria uma nova entrada.

        Args:
            nid: NID do destino
            link: Identificador do link
        """
        self.nid = nid
        self.link = link
        self.timestamp = datetime.now()
        self.packet_count = 0

    def update(self, link: Any):
        """
        Atualiza a entrada (novo link ou refresh timestamp).

        Args:
            link: Novo link
        """
        self.link = link
        self.timestamp = datetime.now()

    def increment_count(self):
        """Incrementa o contador de pacotes."""
        self.packet_count += 1

    def age(self) -> timedelta:
        """
        Retorna a idade da entrada.

        Returns:
            Tempo desde a última atualização
        """
        return datetime.now() - self.timestamp

    def __repr__(self) -> str:
        return f"ForwardingEntry(nid={self.nid}, link={self.link}, age={self.age()}, count={self.packet_count})"


class ForwardingTable:
    """
    Tabela de forwarding para routing na rede IoT.

    Thread-safe.
    """

    def __init__(self, timeout: Optional[int] = 300):
        """
        Inicializa a tabela de forwarding.

        Args:
            timeout: Tempo em segundos para expiração de entradas (None = sem timeout)
        """
        self._table: Dict[NID, ForwardingEntry] = {}
        self._lock = Lock()
        self.timeout = timeout  # segundos

    def learn(self, nid: NID, link: Any):
        """
        Aprende uma rota (associa NID a um link).

        Args:
            nid: NID do destino
            link: Link pelo qual chegou mensagem deste NID
        """
        with self._lock:
            if nid in self._table:
                # Atualizar entrada existente
                entry = self._table[nid]
                if entry.link != link:
                    logger.debug(f"Updating route for {nid}: {entry.link} → {link}")
                entry.update(link)
            else:
                # Nova entrada
                logger.debug(f"Learning new route: {nid} → {link}")
                self._table[nid] = ForwardingEntry(nid, link)

    def lookup(self, nid: NID) -> Optional[Any]:
        """
        Procura o link para um NID.

        Args:
            nid: NID do destino

        Returns:
            Link associado ou None se não encontrado
        """
        with self._lock:
            entry = self._table.get(nid)

            if entry is None:
                return None

            if self.timeout and entry.age().total_seconds() > self.timeout:
                logger.debug(f"Route to {nid} expired (age: {entry.age()})")
                del self._table[nid]
                return None

            # Incrementar contador
            entry.increment_count()
            return entry.link

    def remove(self, nid: NID) -> bool:
        """
        Remove uma entrada da tabela.

        Args:
            nid: NID a remover

        Returns:
            True se foi removido, False se não existia
        """
        with self._lock:
            if nid in self._table:
                logger.debug(f"Removing route for {nid}")
                del self._table[nid]
                return True
            return False

    def remove_by_link(self, link: Any) -> int:
        """
        Remove todas as entradas associadas a um link.

        Útil quando um link é desconectado.

        Args:
            link: Link a remover

        Returns:
            Número de entradas removidas
        """
        with self._lock:
            to_remove = [nid for nid, entry in self._table.items() if entry.link == link]

            for nid in to_remove:
                logger.debug(f"Removing route for {nid} (link {link} down)")
                del self._table[nid]

            if to_remove:
                logger.info(f"Removed {len(to_remove)} routes for link {link}")

            return len(to_remove)

    def clear(self):
        """Limpa toda a tabela."""
        with self._lock:
            count = len(self._table)
            self._table.clear()
            logger.info(f"Cleared forwarding table ({count} entries)")

    def cleanup_expired(self) -> int:
        """
        Remove entradas expiradas.

        Returns:
            Número de entradas removidas
        """
        if not self.timeout:
            return 0

        with self._lock:
            expired = [
                nid
                for nid, entry in self._table.items()
                if entry.age().total_seconds() > self.timeout
            ]

            for nid in expired:
                logger.debug(f"Removing expired route for {nid}")
                del self._table[nid]

            if expired:
                logger.info(f"Cleaned up {len(expired)} expired entries")

            return len(expired)

    def get_all_entries(self) -> Dict[NID, ForwardingEntry]:
        """
        Retorna uma cópia de todas as entradas.

        Returns:
            Dict com todas as entradas
        """
        with self._lock:
            return self._table.copy()

    def size(self) -> int:
        """
        Retorna o número de entradas na tabela.

        Returns:
            Número de entradas
        """
        with self._lock:
            return len(self._table)

    def __len__(self) -> int:
        return self.size()

    def __contains__(self, nid: NID) -> bool:
        with self._lock:
            return nid in self._table

    def __repr__(self) -> str:
        with self._lock:
            entries_str = "\n  ".join(str(e) for e in self._table.values())
            return f"ForwardingTable({len(self._table)} entries):\n  {entries_str}" if self._table else "ForwardingTable(empty)"
