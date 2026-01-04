#!/usr/bin/env python3
"""
Testar scan BLE via D-Bus direto (BlueZ) para ver advertising service UUIDs.
"""
import dbus
import dbus.mainloop.glib
from gi.repository import GLib
import signal
import sys

# Dispositivos encontrados
devices_found = {}

def interfaces_added(path, interfaces):
    """Callback quando um novo dispositivo BLE é descoberto."""
    if 'org.bluez.Device1' not in interfaces:
        return

    props = interfaces['org.bluez.Device1']
    address = props.get('Address', 'Unknown')
    name = props.get('Name', props.get('Alias', 'Unknown'))
    rssi = props.get('RSSI', 'N/A')

    # IMPORTANTE: ServiceData e UUIDs do advertising
    uuids = props.get('UUIDs', [])
    service_data = props.get('ServiceData', {})
    manufacturer_data = props.get('ManufacturerData', {})

    print(f"\n Dispositivo encontrado:")
    print(f"   Endereço: {address}")
    print(f"   Nome: {name}")
    print(f"   RSSI: {rssi}")
    print(f"   UUIDs (advertising): {uuids}")
    print(f"   ServiceData: {service_data}")
    print(f"   ManufacturerData: {len(manufacturer_data)} entries")

    # Guardar
    devices_found[path] = {
        'address': address,
        'name': name,
        'rssi': rssi,
        'uuids': uuids,
    }

def properties_changed(interface, changed, invalidated, path):
    """Callback quando propriedades de um dispositivo mudam."""
    if interface != 'org.bluez.Device1':
        return

    if 'RSSI' in changed or 'UUIDs' in changed:
        # Dispositivo atualizado
        pass

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 test_dbus_scan.py <adapter>")
        print("Exemplo: python3 test_dbus_scan.py hci0")
        return 1

    adapter_name = sys.argv[1]
    adapter_path = f'/org/bluez/{adapter_name}'

    # Configurar D-Bus
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    print("=" * 70)
    print("  SCAN BLE VIA D-BUS (BlueZ direto)")
    print("=" * 70)
    print(f"  Adaptador: {adapter_name}")
    print("=" * 70)
    print()

    try:
        # Obter adaptador
        adapter_obj = bus.get_object('org.bluez', adapter_path)
        adapter_props = dbus.Interface(adapter_obj, 'org.freedesktop.DBus.Properties')
        adapter_iface = dbus.Interface(adapter_obj, 'org.bluez.Adapter1')

        powered = adapter_props.Get('org.bluez.Adapter1', 'Powered')
        print(f"Adaptador powered: {powered}")

        if not powered:
            print("A ligar adaptador...")
            adapter_props.Set('org.bluez.Adapter1', 'Powered', dbus.Boolean(True))

        # Registar callbacks para descoberta
        bus.add_signal_receiver(
            interfaces_added,
            dbus_interface='org.freedesktop.DBus.ObjectManager',
            signal_name='InterfacesAdded'
        )

        bus.add_signal_receiver(
            properties_changed,
            dbus_interface='org.freedesktop.DBus.Properties',
            signal_name='PropertiesChanged',
            path_keyword='path'
        )

        # Iniciar discovery
        print("\n A iniciar discovery (10 segundos)...")
        print()
        adapter_iface.StartDiscovery()

        # Event loop
        loop = GLib.MainLoop()

        def timeout():
            print("\n  Timeout - A parar discovery...")
            try:
                adapter_iface.StopDiscovery()
            except:
                pass
            loop.quit()
            return False

        def signal_handler(sig, frame):
            print("\n Interrompido pelo utilizador")
            try:
                adapter_iface.StopDiscovery()
            except:
                pass
            loop.quit()

        signal.signal(signal.SIGINT, signal_handler)
        GLib.timeout_add_seconds(10, timeout)

        loop.run()

        # Resultados
        print("\n" + "=" * 70)
        print(f"RESUMO: {len(devices_found)} dispositivos encontrados")
        print("=" * 70)

        for path, dev in devices_found.items():
            print(f"\n{dev['address']} ({dev['name']})")
            print(f"  UUIDs: {dev['uuids']}")

            iot_uuid_full = '12340000-0000-1000-8000-00805f9b34fb'
            iot_uuid_short = '00001234-0000-1000-8000-00805f9b34fb'

            has_iot = any(
                uuid.lower() == iot_uuid_full.lower() or
                uuid.lower() == iot_uuid_short.lower() or
                uuid.lower().startswith('12340000')
                for uuid in dev['uuids']
            )

            if has_iot:
                print(f"   TEM IoT Service UUID!")

        print()

    except dbus.exceptions.DBusException as e:
        print(f" Erro D-Bus: {e}")
        return 1
    except Exception as e:
        print(f" Erro: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
