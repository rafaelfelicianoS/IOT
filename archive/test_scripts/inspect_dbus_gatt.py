#!/usr/bin/env python3
"""
Inspeciona o que está registado no BlueZ via D-Bus.
"""
import dbus

def main():
    bus = dbus.SystemBus()

    # Ver o GattManager1
    try:
        adapter_obj = bus.get_object('org.bluez', '/org/bluez/hci0')

        print("=" * 70)
        print("  GATT SERVICES REGISTADOS NO BLUEZ")
        print("=" * 70)
        print()

        # Listar todos os objetos sob /org/bluez
        manager = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager')
        objects = manager.GetManagedObjects()

        print("Objetos encontrados:")
        for path, interfaces in objects.items():
            if 'org.bluez.GattService1' in interfaces:
                props = interfaces['org.bluez.GattService1']
                uuid = props.get('UUID', 'N/A')
                primary = props.get('Primary', 'N/A')
                print(f"  Service: {path}")
                print(f"    UUID: {uuid}")
                print(f"    Primary: {primary}")
                print()

    except Exception as e:
        print(f"Erro ao inspecionar GATT Manager: {e}")
        import traceback
        traceback.print_exc()

    print("=" * 70)
    print("  ADVERTISEMENTS REGISTADOS NO BLUEZ")
    print("=" * 70)
    print()

    try:
        # Ver LEAdvertisingManager1
        adv_manager_obj = bus.get_object('org.bluez', '/org/bluez/hci0')
        adv_manager_props = dbus.Interface(adv_manager_obj, 'org.freedesktop.DBus.Properties')

        # Get ActiveInstances
        active = adv_manager_props.Get('org.bluez.LEAdvertisingManager1', 'ActiveInstances')
        print(f"Active Advertisement Instances: {active}")
        print()

        # Listar advertisements via ObjectManager
        for path, interfaces in objects.items():
            if 'org.bluez.LEAdvertisement1' in interfaces:
                props = interfaces['org.bluez.LEAdvertisement1']
                print(f"  Advertisement (via ObjectManager): {path}")
                print(f"    Type: {props.get('Type', 'N/A')}")
                print(f"    ServiceUUIDs: {props.get('ServiceUUIDs', [])}")
                print(f"    LocalName: {props.get('LocalName', 'N/A')}")
                print()

        # Tentar aceder diretamente ao nosso advertisement
        print("  A tentar aceder diretamente ao nosso advertisement:")
        try:
            our_adv_obj = bus.get_object('org.bluez', '/org/bluez/iot/advertisement0')
            our_adv_props = dbus.Interface(our_adv_obj, 'org.freedesktop.DBus.Properties')
            adv_type = our_adv_props.Get('org.bluez.LEAdvertisement1', 'Type')
            adv_uuids = our_adv_props.Get('org.bluez.LEAdvertisement1', 'ServiceUUIDs')
            print(f"    Path: /org/bluez/iot/advertisement0")
            print(f"    Type: {adv_type}")
            print(f"    ServiceUUIDs: {adv_uuids}")
            print()
        except dbus.exceptions.DBusException as e:
            print(f"    ❌ Não foi possível aceder: {e}")
            print()

    except Exception as e:
        print(f"Erro ao inspecionar LEAdvertisingManager: {e}")
        import traceback
        traceback.print_exc()

    return 0

if __name__ == '__main__':
    exit(main())
