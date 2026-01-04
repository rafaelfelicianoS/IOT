#!/usr/bin/env python3
"""
Helper para operações BLE usando Bleak.

Bleak é usado para operações de WRITE no Linux porque SimpleBLE
não consegue escrever em características GATT.
"""

import asyncio
from typing import Optional
from bleak import BleakClient, BleakScanner
from loguru import logger


class BleakWriteHelper:
    """Helper para operações de escrita GATT usando Bleak."""

    @staticmethod
    async def write_characteristic_async(
        device_address: str,
        char_uuid: str,
        data: bytes,
        timeout: float = 10.0
    ) -> bool:
        """
        Escreve dados numa característica usando Bleak (async).

        Args:
            device_address: Endereço MAC do dispositivo
            char_uuid: UUID da característica
            data: Dados a escrever
            timeout: Timeout em segundos

        Returns:
            True se escrita bem-sucedida
        """
        try:
            # Fazer scan rápido para obter BLEDevice object
            logger.debug(f"Bleak: A fazer scan para encontrar {device_address}...")
            devices = await BleakScanner.discover(timeout=3.0, return_adv=True)

            target = None
            for device, _ in devices.values():
                if device.address.upper() == device_address.upper():
                    target = device
                    break

            if not target:
                logger.error(f"Bleak: Dispositivo {device_address} não encontrado no scan")
                return False

            # Conectar e escrever
            logger.debug(f"Bleak: A conectar a {device_address}...")
            async with BleakClient(target, timeout=timeout) as client:
                logger.debug(f"Bleak: Conectado, a escrever {len(data)} bytes em {char_uuid}...")
                await client.write_gatt_char(char_uuid, data, response=True)
                logger.debug(f"Bleak:  Escrita bem-sucedida!")
                return True

        except Exception as e:
            logger.error(f"Bleak: Erro ao escrever: {e}")
            return False

    @staticmethod
    def write_characteristic(
        device_address: str,
        char_uuid: str,
        data: bytes,
        timeout: float = 10.0
    ) -> bool:
        """
        Escreve dados numa característica usando Bleak (sync wrapper).

        Args:
            device_address: Endereço MAC do dispositivo
            char_uuid: UUID da característica
            data: Dados a escrever
            timeout: Timeout em segundos

        Returns:
            True se escrita bem-sucedida
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                BleakWriteHelper.write_characteristic_async(
                    device_address,
                    char_uuid,
                    data,
                    timeout
                )
            )
        finally:
            loop.close()
