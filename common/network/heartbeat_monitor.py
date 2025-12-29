"""
Heartbeat Monitor - Deteta timeouts de heartbeat e gerencia estado de uplink.

Este módulo implementa a detecção de falhas de link baseada em heartbeats,
conforme especificado na Seção 3.2 (Network liveness) do projeto.
"""

import time
import threading
from typing import Optional, Callable
from loguru import logger


class HeartbeatMonitor:
    """
    Monitor de heartbeats para detetar falhas de uplink.

    Funcionalidade:
    - Conta heartbeats perdidos consecutivos
    - Considera uplink morto após 3 heartbeats perdidos (15 segundos)
    - Notifica callbacks quando timeout é detetado
    """

    def __init__(
        self,
        heartbeat_interval: float = 5.0,
        max_missed: int = 3,
        on_timeout: Optional[Callable[[], None]] = None
    ):
        """
        Inicializa o monitor de heartbeats.

        Args:
            heartbeat_interval: Intervalo esperado entre heartbeats (segundos)
            max_missed: Número máximo de heartbeats perdidos antes de timeout
            on_timeout: Callback chamado quando timeout é detetado
        """
        self.heartbeat_interval = heartbeat_interval
        self.max_missed = max_missed
        self.on_timeout = on_timeout

        # Estado interno
        self._last_heartbeat_time: Optional[float] = None
        self._missed_count: int = 0
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        logger.debug(
            f"HeartbeatMonitor criado: interval={heartbeat_interval}s, "
            f"max_missed={max_missed}"
        )

    def start(self):
        """Inicia o monitoramento de heartbeats."""
        if self._monitoring:
            logger.warning("HeartbeatMonitor já está a correr")
            return

        self._monitoring = True
        self._stop_event.clear()
        self._missed_count = 0
        self._last_heartbeat_time = time.time()  # Inicia timer

        # Thread de monitoramento
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self._monitor_thread.start()

        logger.info(
            f"💓 HeartbeatMonitor iniciado: verificação a cada "
            f"{self.heartbeat_interval}s, timeout após {self.max_missed} misses"
        )

    def stop(self):
        """Para o monitoramento de heartbeats."""
        if not self._monitoring:
            return

        self._monitoring = False
        self._stop_event.set()

        if self._monitor_thread:
            # Não fazer join se estamos na própria thread
            if threading.current_thread() != self._monitor_thread:
                self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None

        logger.info("HeartbeatMonitor parado")

    def on_heartbeat_received(self, sequence: int):
        """
        Notifica que um heartbeat foi recebido.

        Args:
            sequence: Número de sequência do heartbeat
        """
        self._last_heartbeat_time = time.time()

        if self._missed_count > 0:
            logger.info(
                f"💓 Heartbeat recebido (seq={sequence}), "
                f"contador resetado (estava em {self._missed_count})"
            )
        else:
            logger.debug(f"💓 Heartbeat recebido (seq={sequence})")

        self._missed_count = 0

    def _monitor_loop(self):
        """Loop principal de monitoramento (roda em thread separada)."""
        while not self._stop_event.is_set():
            # Aguardar intervalo de heartbeat
            if self._stop_event.wait(timeout=self.heartbeat_interval):
                break  # Stop foi chamado

            # Verificar se recebemos heartbeat recentemente
            if self._last_heartbeat_time is None:
                continue  # Ainda não recebemos nenhum heartbeat

            time_since_last = time.time() - self._last_heartbeat_time

            # Se passou mais de 1 intervalo sem heartbeat
            if time_since_last >= self.heartbeat_interval:
                self._missed_count += 1

                logger.warning(
                    f"⚠️  Heartbeat perdido! Contador: {self._missed_count}/{self.max_missed} "
                    f"(último há {time_since_last:.1f}s)"
                )

                # Verificar se atingimos o máximo
                if self._missed_count >= self.max_missed:
                    logger.error(
                        f"❌ TIMEOUT DE HEARTBEAT! Perdidos {self._missed_count} "
                        f"heartbeats consecutivos"
                    )

                    # Chamar callback de timeout
                    if self.on_timeout:
                        try:
                            self.on_timeout()
                        except Exception as e:
                            logger.error(f"Erro no callback de timeout: {e}")

                    # Parar monitoramento (uplink está morto)
                    self._monitoring = False
                    break

    def get_missed_count(self) -> int:
        """Retorna número de heartbeats perdidos consecutivos."""
        return self._missed_count

    def is_monitoring(self) -> bool:
        """Verifica se está a monitorar."""
        return self._monitoring

    def get_time_since_last(self) -> Optional[float]:
        """Retorna tempo (segundos) desde último heartbeat."""
        if self._last_heartbeat_time is None:
            return None
        return time.time() - self._last_heartbeat_time
