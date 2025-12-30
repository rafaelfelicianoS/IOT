#!/usr/bin/env python3
"""
Handler de Autenticação para GATT Server/Client.

Este módulo integra o AuthenticationProtocol com a AuthCharacteristic do BLE,
gerindo automaticamente o handshake de autenticação quando um dispositivo conecta.
"""

from typing import Optional, Callable, Dict
from common.utils.logger import get_logger
from common.security.certificate_manager import CertificateManager
from common.security.authentication import AuthenticationProtocol, AuthState

logger = get_logger("auth_handler")


class AuthenticationHandler:
    """
    Handler de autenticação para servidor GATT.

    Gere múltiplas sessões de autenticação (uma por cliente conectado).
    """

    def __init__(self, cert_manager: CertificateManager):
        """
        Inicializa o handler de autenticação.

        Args:
            cert_manager: Certificate Manager inicializado
        """
        self.cert_manager = cert_manager

        # Sessões de autenticação por cliente (key = sender/device_address)
        self.sessions: Dict[str, AuthenticationProtocol] = {}

        # Callbacks
        self.on_authenticated: Optional[Callable[[str, dict], None]] = None
        self.on_auth_failed: Optional[Callable[[str], None]] = None

        logger.info("AuthenticationHandler inicializado")

    def set_authenticated_callback(self, callback: Callable[[str, dict], None]):
        """
        Define callback chamado quando autenticação é bem sucedida.

        Args:
            callback: Função (client_id, peer_info) -> None
        """
        self.on_authenticated = callback

    def set_auth_failed_callback(self, callback: Callable[[str], None]):
        """
        Define callback chamado quando autenticação falha.

        Args:
            callback: Função (client_id) -> None
        """
        self.on_auth_failed = callback

    def get_or_create_session(self, client_id: str) -> AuthenticationProtocol:
        """
        Obtém ou cria sessão de autenticação para um cliente.

        Args:
            client_id: ID do cliente (endereço BLE ou sender D-Bus)

        Returns:
            Protocolo de autenticação para este cliente
        """
        if client_id not in self.sessions:
            logger.info(f"Nova sessão de autenticação para cliente: {client_id}")
            self.sessions[client_id] = AuthenticationProtocol(self.cert_manager)

        return self.sessions[client_id]

    def handle_auth_message(self, auth_data: bytes, client_id: str) -> Optional[bytes]:
        """
        Processa mensagem de autenticação recebida de um cliente.

        Este é o callback que deve ser registado na AuthCharacteristic.

        Args:
            auth_data: Dados de autenticação recebidos
            client_id: ID do cliente

        Returns:
            Resposta a enviar ao cliente (None se não há resposta)
        """
        logger.info(f"📨 Mensagem de autenticação de {client_id}: {len(auth_data)} bytes")

        # Obter ou criar sessão
        auth_protocol = self.get_or_create_session(client_id)

        try:
            # Processar mensagem
            continue_auth, response = auth_protocol.process_message(auth_data)

            logger.debug(f"   Estado da sessão: {auth_protocol.state.name}")

            # Verificar se autenticação terminou
            if auth_protocol.state == AuthState.AUTHENTICATED:
                logger.info(f"✅ Cliente {client_id} AUTENTICADO!")

                # Chamar callback de sucesso
                if self.on_authenticated:
                    peer_info = auth_protocol.get_peer_info()
                    self.on_authenticated(client_id, peer_info)

            elif auth_protocol.state == AuthState.FAILED:
                logger.error(f"❌ Autenticação falhou para cliente {client_id}")

                # Chamar callback de falha
                if self.on_auth_failed:
                    self.on_auth_failed(client_id)

                # Limpar sessão falhada
                self.remove_session(client_id)

            return response

        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagem de autenticação: {e}")
            logger.exception(e)

            # Limpar sessão com erro
            self.remove_session(client_id)

            return None

    def initiate_authentication(self, client_id: str) -> bytes:
        """
        Inicia processo de autenticação com um cliente.

        Args:
            client_id: ID do cliente

        Returns:
            Mensagem inicial (CERT_OFFER) para enviar ao cliente
        """
        auth_protocol = self.get_or_create_session(client_id)
        return auth_protocol.start_authentication()

    def is_authenticated(self, client_id: str) -> bool:
        """
        Verifica se um cliente está autenticado.

        Args:
            client_id: ID do cliente

        Returns:
            True se autenticado, False caso contrário
        """
        if client_id not in self.sessions:
            return False

        return self.sessions[client_id].is_authenticated()

    def get_peer_info(self, client_id: str) -> Optional[dict]:
        """
        Obtém informações do peer autenticado.

        Args:
            client_id: ID do cliente

        Returns:
            Informações do peer ou None se não autenticado
        """
        if client_id not in self.sessions:
            return None

        return self.sessions[client_id].get_peer_info()

    def remove_session(self, client_id: str):
        """
        Remove sessão de autenticação de um cliente.

        Args:
            client_id: ID do cliente
        """
        if client_id in self.sessions:
            logger.info(f"Removendo sessão de autenticação: {client_id}")
            del self.sessions[client_id]

    def get_authenticated_clients(self) -> list:
        """
        Obtém lista de clientes autenticados.

        Returns:
            Lista de client IDs autenticados
        """
        return [
            client_id
            for client_id, session in self.sessions.items()
            if session.is_authenticated()
        ]
