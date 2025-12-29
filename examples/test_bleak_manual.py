#!/usr/bin/env python3
"""
Manual Bleak connection test that explicitly sets address type before connecting.
"""
import asyncio
from bleak import BleakClient, BleakScanner
from bleak.backends.bluezdbus.defs import device_interface
import dbus_fast

TARGET_ADDRESS = "E0:D3:62:D6:EE:A0"

async def main():
    print("🔍 Scanning for BLE devices...")
    devices = await BleakScanner.discover(timeout=5.0, return_adv=True)

    target = None
    for device, adv_data in devices.values():
        if device.address.upper() == TARGET_ADDRESS.upper():
            target = device
            print(f"✅ Found: {device.name} ({device.address})")
            print(f"   RSSI: {adv_data.rssi}")
            print(f"   Address Type: {device.details.get('props', {}).get('AddressType')}")
            break

    if not target:
        print(f"❌ Device {TARGET_ADDRESS} not found!")
        return

    print(f"\n🔌 Connecting with 30s timeout...")
    try:
        async with BleakClient(target, timeout=30.0) as client:
            print(f"✅ Connected: {client.is_connected}")

            print(f"\n📡 Services:")
            for service in client.services:
                print(f"   {service.uuid}")
                for char in service.characteristics:
                    print(f"      └─ {char.uuid} ({char.properties})")

    except Exception as e:
        print(f"❌ Connection failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
