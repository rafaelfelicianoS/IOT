#!/usr/bin/env python3
"""
Script para diagnosticar o que o D-Bus vê após conexão BLE.
"""
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

import dbus
import time
from common.ble.gatt_client import BLEClient

def inspect_dbus_tree(device_address: str):
    """Inspeciona toda a árvore D-Bus do dispositivo."""
    bus = dbus.SystemBus()
    device_path = f"/org/bluez/hci0/dev_{device_address.replace(':', '_')}"

    print(f"\n{'='*60}")
    print(f"Inspecionando D-Bus para: {device_address}")
    print(f"Device path: {device_path}")
    print(f"{'='*60}\n")

    try:
        # 1. Verificar propriedades do dispositivo
        device_obj = bus.get_object("org.bluez", device_path)
        device_props = dbus.Interface(device_obj, "org.freedesktop.DBus.Properties")

        print("📱 Propriedades do Dispositivo:")
        for prop in ["Connected", "ServicesResolved", "UUIDs"]:
            try:
                value = device_props.Get("org.bluez.Device1", prop)
                print(f"   {prop}: {value}")
            except Exception as e:
                print(f"   {prop}: ERROR - {e}")

        # 2. Listar todos os objetos D-Bus sob o device path
        obj_manager = dbus.Interface(
            bus.get_object("org.bluez", "/"),
            "org.freedesktop.DBus.ObjectManager"
        )
        objects = obj_manager.GetManagedObjects()

        device_objects = [(path, interfaces) for path, interfaces in objects.items()
                          if path.startswith(device_path)]

        print(f"\n📂 Objetos D-Bus encontrados: {len(device_objects)}")
        for path, interfaces in device_objects:
            print(f"   {path}")
            for iface_name in interfaces.keys():
                print(f"      ↳ {iface_name}")
                if iface_name == "org.bluez.GattService1":
                    uuid = interfaces[iface_name].get('UUID', 'unknown')
                    primary = interfaces[iface_name].get('Primary', False)
                    print(f"         UUID: {uuid}, Primary: {primary}")
                elif iface_name == "org.bluez.GattCharacteristic1":
                    uuid = interfaces[iface_name].get('UUID', 'unknown')
                    flags = interfaces[iface_name].get('Flags', [])
                    print(f"         UUID: {uuid}, Flags: {flags}")

        # 3. Procurar especificamente pelo nosso serviço
        print(f"\n🔍 Procurando serviço IoT (12340000-0000-1000-8000-00805f9b34fb):")
        iot_service_found = False
        for path, interfaces in device_objects:
            if "org.bluez.GattService1" in interfaces:
                uuid = interfaces["org.bluez.GattService1"].get('UUID', '').lower()
                if uuid == "12340000-0000-1000-8000-00805f9b34fb":
                    print(f"   ✅ Serviço encontrado: {path}")
                    iot_service_found = True

        if not iot_service_found:
            print("   ❌ Serviço IoT NÃO encontrado no D-Bus!")

    except Exception as e:
        print(f"❌ Erro ao inspecionar D-Bus: {e}")

def main():
    TARGET_ADDRESS = "E0:D3:62:D6:EE:A0"

    print("🔌 Conectando ao servidor BLE...")
    client = BLEClient(adapter_index=0)

    # Scan
    devices = client.scanner.scan(duration_ms=5000, filter_iot=True)
    if not devices:
        print("❌ Nenhum dispositivo encontrado!")
        return

    print(f"✅ Dispositivo encontrado: {devices[0].address}")

    # Procurar o dispositivo alvo
    target = None
    for dev in devices:
        if dev.address.upper() == TARGET_ADDRESS.upper():
            target = dev
            break
    
    if not target:
        print(f"❌ Dispositivo {TARGET_ADDRESS} não encontrado!")
        return

    # Conectar
    conn = client.connect_to_device(target)
    if not conn:
        print("❌ Falha ao conectar!")
        return

    print("✅ Conectado! A verificar conexão...")

    # Verificar se a conexão se mantém
    for i in range(10):
        time.sleep(1)
        still_connected = conn.is_connected
        print(f"   Segundo {i+1}/10: SimpleBLE connected={still_connected}")

        if not still_connected:
            print(f"   ❌ Conexão perdida após {i+1} segundos!")
            break
    else:
        print(f"   ✅ Conexão manteve-se durante 10 segundos!")

    print()

    # Tentar ler serviços via SimpleBLE
    print("🔍 A tentar descobrir serviços via SimpleBLE...")
    try:
        services = conn.peripheral.services()
        print(f"   SimpleBLE encontrou {len(services)} serviços:")
        for svc in services:
            print(f"      - {svc.uuid()}")
            try:
                characteristics = svc.characteristics()
                print(f"        {len(characteristics)} características")
                for char in characteristics:
                    print(f"          - {char.uuid()}")
            except Exception as e:
                print(f"        ❌ Erro ao ler características: {e}")
    except Exception as e:
        print(f"   ❌ Erro ao ler serviços: {e}")

    print()

    # Inspecionar D-Bus
    inspect_dbus_tree(TARGET_ADDRESS)

    # Desconectar
    print(f"\n{'='*60}")
    print("🔌 A desconectar...")
    client.disconnect_from_device(TARGET_ADDRESS)
    print("✅ Desconectado!")

if __name__ == "__main__":
    main()
