#!/usr/bin/env python3
"""
Test script using Bleak library to see if it can enumerate GATT characteristics.
Bleak is a pure Python BLE library that should work better on Linux than SimpleBLE.

Install: pip install bleak
"""
import asyncio
from bleak import BleakClient, BleakScanner

TARGET_ADDRESS = "E0:D3:62:D6:EE:A0"
SERVICE_UUID = "12340000-0000-1000-8000-00805f9b34fb"
CHAR_UUID = "12340001-0000-1000-8000-00805f9b34fb"

async def main():
    print("🔍 Scanning for BLE devices...")
    devices = await BleakScanner.discover(timeout=5.0)

    target = None
    for device in devices:
        print(f"   Found: {device.address} ({device.name})")
        if device.address.upper() == TARGET_ADDRESS.upper():
            target = device

    if not target:
        print(f"❌ Device {TARGET_ADDRESS} not found!")
        return

    print(f"\n✅ Target found: {target.name} ({target.address})")
    print(f"\n🔌 Connecting...")

    # Force LE (Low Energy) address type to avoid Bluetooth Classic connection
    async with BleakClient(target.address, address_type="public") as client:
        print(f"✅ Connected: {client.is_connected}")

        print(f"\n📡 Discovering services...")
        for service in client.services:
            print(f"\n   Service: {service.uuid}")
            for char in service.characteristics:
                print(f"      Characteristic: {char.uuid}")
                print(f"         Properties: {char.properties}")

        # Find our IoT service
        print(f"\n🔍 Looking for IoT service {SERVICE_UUID}...")
        iot_service = None
        for service in client.services:
            if service.uuid.lower() == SERVICE_UUID.lower():
                iot_service = service
                print(f"   ✅ IoT service found!")
                break

        if not iot_service:
            print(f"   ❌ IoT service not found!")
            return

        # Find the NETWORK_PACKET characteristic
        print(f"\n🔍 Looking for characteristic {CHAR_UUID}...")
        packet_char = None
        for char in iot_service.characteristics:
            if char.uuid.lower() == CHAR_UUID.lower():
                packet_char = char
                print(f"   ✅ Characteristic found!")
                print(f"      Properties: {char.properties}")
                break

        if not packet_char:
            print(f"   ❌ Characteristic not found!")
            return

        # Try to write some test data
        print(f"\n✍️  Attempting to write test data...")
        test_data = b"Hello from Bleak!"
        try:
            await client.write_gatt_char(packet_char.uuid, test_data, response=True)
            print(f"   ✅ Write successful!")
        except Exception as e:
            print(f"   ❌ Write failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
