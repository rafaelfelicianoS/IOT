"""
Sistema de logging centralizado usando Loguru.

Fornece logging formatado para ficheiros e consola.
"""

import sys
from pathlib import Path
from loguru import logger
from common.utils.config import config


def setup_logger(
    module_name: str = "iot-network",
    log_to_file: bool = True,
    log_to_console: bool = True,
) -> logger:
    """
    Configura o logger para o módulo especificado.

    Args:
        module_name: Nome do módulo (usado no nome do ficheiro de log)
        log_to_file: Se True, faz log para ficheiro
        log_to_console: Se True, faz log para consola

    Returns:
        Logger configurado
    """
    # Remover handlers default
    logger.remove()

    # Formato para consola (mais simples)
    console_format = (
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
        "<level>{message}</level>"
    )

    # Formato para ficheiro (mais detalhado)
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    # Log para consola
    if log_to_console:
        logger.add(
            sys.stderr,
            format=console_format,
            level=config.log_level,
            colorize=True,
        )

    # Log para ficheiro
    if log_to_file:
        try:
            # Garantir que o diretório existe
            config.ensure_directories_exist()

            log_file = config.logs_dir / f"{module_name}.log"

            logger.add(
                log_file,
                format=file_format,
                level=config.log_level,
                rotation="10 MB",      # Rotação quando atingir 10MB
                retention="7 days",    # Manter logs dos últimos 7 dias
                compression="zip",     # Comprimir logs antigos
                enqueue=True,          # Thread-safe
            )
        except (PermissionError, OSError) as e:
            # Se não tiver permissões, fazer log apenas para consola
            # (não falhar - continuar sem ficheiro de log)
            print(f"  Aviso: Não foi possível criar ficheiro de log: {e}", file=sys.stderr)
            print(f"   Logs apenas na consola.", file=sys.stderr)

    return logger


# Logger default para uso geral
default_logger = setup_logger()


def get_logger(name: str) -> logger:
    """
    Obtém um logger com contexto específico.

    Args:
        name: Nome do contexto (ex: "sink", "node", "gatt_server")

    Returns:
        Logger com contexto
    """
    return logger.bind(name=name)
