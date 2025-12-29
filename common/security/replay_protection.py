"""
Proteção contra Replay Attacks.

Implementa tracking de sequence numbers para detetar e prevenir
replay attacks (pacotes duplicados ou reordenados).

Estratégia:
- Mantém registo dos últimos sequence numbers recebidos por cada source NID
- Rejeita pacotes com sequence numbers já vistos (duplicados)
- Rejeita pacotes com sequence numbers muito antigos (janela deslizante)
"""

from typing import Dict, Set
from common.utils.nid import NID
from common.utils.logger import get_logger

logger = get_logger("replay_protection")

# Tamanho da janela de sequence numbers aceites
# Permite reordenamento até WINDOW_SIZE pacotes
SEQUENCE_WINDOW_SIZE = 100


class ReplayProtection:
    """
    Protetor contra replay attacks usando sequence numbers.

    Mantém tracking dos sequence numbers já vistos por cada source NID
    e rejeita pacotes duplicados ou muito antigos.
    """

    def __init__(self, window_size: int = SEQUENCE_WINDOW_SIZE):
        """
        Inicializa o protetor de replay.

        Args:
            window_size: Tamanho da janela de sequence numbers aceites
        """
        self.window_size = window_size

        # Tracking por source NID:
        # source_nid -> (highest_seq_seen, set_of_seen_sequences_in_window)
        self.tracking: Dict[str, tuple[int, Set[int]]] = {}

        logger.info(f"ReplayProtection iniciado (window_size={window_size})")

    def check_and_update(self, source_nid: NID, sequence: int) -> bool:
        """
        Verifica se um pacote é válido (não é replay) e atualiza tracking.

        Args:
            source_nid: NID do source do pacote
            sequence: Número de sequência do pacote

        Returns:
            True se o pacote é válido (não é replay), False caso contrário
        """
        source_key = str(source_nid)

        # Primeira vez que vemos este source
        if source_key not in self.tracking:
            self.tracking[source_key] = (sequence, {sequence})
            logger.debug(
                f"Novo source {source_nid.to_short_string()}: "
                f"seq={sequence} (primeiro pacote)"
            )
            return True

        highest_seq, seen_seqs = self.tracking[source_key]

        # Verificar se sequence já foi visto (REPLAY!)
        if sequence in seen_seqs:
            logger.warning(
                f"🚨 REPLAY DETECTADO! Source: {source_nid.to_short_string()}, "
                f"seq={sequence} (já foi visto)"
            )
            return False

        # Verificar se sequence está fora da janela (muito antigo)
        if sequence < highest_seq - self.window_size:
            logger.warning(
                f"🚨 REPLAY DETECTADO! Source: {source_nid.to_short_string()}, "
                f"seq={sequence} (muito antigo, highest={highest_seq}, "
                f"window={self.window_size})"
            )
            return False

        # Pacote válido - atualizar tracking
        seen_seqs.add(sequence)

        # Atualizar highest_seq se necessário
        if sequence > highest_seq:
            new_highest = sequence

            # Limpar sequences antigas fora da nova janela
            min_valid_seq = new_highest - self.window_size
            seen_seqs = {seq for seq in seen_seqs if seq > min_valid_seq}

            self.tracking[source_key] = (new_highest, seen_seqs)

            logger.debug(
                f"Source {source_nid.to_short_string()}: "
                f"seq={sequence} (novo highest, window: {len(seen_seqs)} seqs)"
            )
        else:
            # Sequence dentro da janela mas não é o maior
            # (reordenamento aceitável)
            self.tracking[source_key] = (highest_seq, seen_seqs)

            logger.debug(
                f"Source {source_nid.to_short_string()}: "
                f"seq={sequence} (dentro da janela, highest={highest_seq})"
            )

        return True

    def reset_source(self, source_nid: NID):
        """
        Remove tracking de um source (útil quando device desconecta).

        Args:
            source_nid: NID do source a remover
        """
        source_key = str(source_nid)

        if source_key in self.tracking:
            del self.tracking[source_key]
            logger.info(f"Tracking removido para source: {source_nid.to_short_string()}")

    def get_stats(self) -> dict:
        """
        Obtém estatísticas do protetor de replay.

        Returns:
            Dicionário com estatísticas
        """
        return {
            'tracked_sources': len(self.tracking),
            'window_size': self.window_size,
            'sources': {
                source_key: {
                    'highest_seq': highest_seq,
                    'sequences_in_window': len(seen_seqs),
                }
                for source_key, (highest_seq, seen_seqs) in self.tracking.items()
            }
        }
