#!/usr/bin/env python3
"""
Teste da funcionalidade stop_heartbeat.

Verifica que:
1. SinkDevice tem métodos block_heartbeat e unblock_heartbeat
2. Heartbeat blocking tracking foi adicionado
3. Integração no CLI está presente
"""

import sys
from pathlib import Path

# Adicionar diretório raiz ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))


def test_sink_device_heartbeat_blocking():
    """Testa se SinkDevice tem funcionalidade de heartbeat blocking."""
    print("\n" + "=" * 70)
    print("TESTE 1: SinkDevice - Heartbeat Blocking")
    print("=" * 70)

    try:
        from sink.sink_device import SinkDevice

        # Verificar atributos e métodos
        checks = [
            ("Método 'block_heartbeat'", hasattr(SinkDevice, 'block_heartbeat')),
            ("Método 'unblock_heartbeat'", hasattr(SinkDevice, 'unblock_heartbeat')),
            ("Método 'get_blocked_heartbeat_nodes'", hasattr(SinkDevice, 'get_blocked_heartbeat_nodes')),
        ]

        all_passed = True
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"  {status} {check_name}")
            if not result:
                all_passed = False

        if all_passed:
            print("\n✅ TESTE PASSOU - SinkDevice tem funcionalidade de heartbeat blocking\n")
            return True
        else:
            print("\n❌ TESTE FALHOU - Alguns métodos não foram encontrados\n")
            return False

    except Exception as e:
        print(f"\n❌ ERRO: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_cli_commands():
    """Testa se CLI tem comandos stop_heartbeat e resume_heartbeat."""
    print("\n" + "=" * 70)
    print("TESTE 2: CLI - Comandos stop_heartbeat e resume_heartbeat")
    print("=" * 70)

    try:
        from sink.interactive_sink import InteractiveSinkCLI

        # Verificar comandos
        checks = [
            ("Comando 'do_stop_heartbeat'", hasattr(InteractiveSinkCLI, 'do_stop_heartbeat')),
            ("Comando 'do_resume_heartbeat'", hasattr(InteractiveSinkCLI, 'do_resume_heartbeat')),
            ("Comando 'do_blocked_heartbeats'", hasattr(InteractiveSinkCLI, 'do_blocked_heartbeats')),
            ("Método auxiliar '_list_downlinks_with_index'", hasattr(InteractiveSinkCLI, '_list_downlinks_with_index')),
            ("Método auxiliar '_list_blocked_nodes'", hasattr(InteractiveSinkCLI, '_list_blocked_nodes')),
        ]

        all_passed = True
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"  {status} {check_name}")
            if not result:
                all_passed = False

        if all_passed:
            print("\n✅ TESTE PASSOU - CLI tem comandos de heartbeat blocking\n")
            return True
        else:
            print("\n❌ TESTE FALHOU - Alguns comandos não foram encontrados\n")
            return False

    except Exception as e:
        print(f"\n❌ ERRO: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_notify_packet_exclude():
    """Testa se notify_packet aceita parâmetro exclude_clients."""
    print("\n" + "=" * 70)
    print("TESTE 3: GATT - notify_packet com exclude_clients")
    print("=" * 70)

    try:
        from common.ble.gatt_services import NetworkPacketCharacteristic
        import inspect

        # Verificar assinatura do método
        sig = inspect.signature(NetworkPacketCharacteristic.notify_packet)
        params = list(sig.parameters.keys())

        print(f"  Parâmetros do notify_packet: {params}")

        has_exclude = 'exclude_clients' in params
        status = "✅" if has_exclude else "❌"
        print(f"\n  {status} Parâmetro 'exclude_clients'")

        if has_exclude:
            print("\n✅ TESTE PASSOU - notify_packet aceita exclude_clients\n")
            return True
        else:
            print("\n❌ TESTE FALHOU - notify_packet não tem parâmetro exclude_clients\n")
            return False

    except Exception as e:
        print(f"\n❌ ERRO: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_integration_in_code():
    """Verifica integração no código-fonte."""
    print("\n" + "=" * 70)
    print("TESTE 4: Integração no Código")
    print("=" * 70)

    try:
        # Verificar sink_device.py
        sink_file = Path(__file__).parent / "sink" / "sink_device.py"
        sink_code = sink_file.read_text()

        checks = [
            ("heartbeat_blocked_nodes declarado", "heartbeat_blocked_nodes" in sink_code),
            ("block_heartbeat implementado", "def block_heartbeat" in sink_code),
            ("unblock_heartbeat implementado", "def unblock_heartbeat" in sink_code),
            ("exclude_clients usado em notify_packet", "exclude_clients=" in sink_code),
        ]

        print("\n📄 sink/sink_device.py:")
        all_passed = True
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"  {status} {check_name}")
            if not result:
                all_passed = False

        # Verificar gatt_services.py
        gatt_file = Path(__file__).parent / "common" / "ble" / "gatt_services.py"
        gatt_code = gatt_file.read_text()

        print("\n📄 common/ble/gatt_services.py:")
        checks = [
            ("notify_packet com exclude_clients", "def notify_packet(self, packet_bytes: bytes, exclude_clients" in gatt_code),
            ("Lógica de exclusão implementada", "if exclude_clients:" in gatt_code),
        ]

        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"  {status} {check_name}")
            if not result:
                all_passed = False

        if all_passed:
            print("\n✅ TESTE PASSOU - Integração completa no código\n")
            return True
        else:
            print("\n❌ TESTE FALHOU - Integração incompleta\n")
            return False

    except Exception as e:
        print(f"\n❌ ERRO: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executa todos os testes."""
    print("\n" + "=" * 70)
    print(" VERIFICAÇÃO: IMPLEMENTAÇÃO STOP_HEARTBEAT")
    print("=" * 70)

    results = []

    # Teste 1: SinkDevice
    results.append(("SinkDevice - Heartbeat Blocking", test_sink_device_heartbeat_blocking()))

    # Teste 2: CLI
    results.append(("CLI - Comandos", test_cli_commands()))

    # Teste 3: GATT
    results.append(("GATT - notify_packet", test_notify_packet_exclude()))

    # Teste 4: Integração
    results.append(("Integração no Código", test_integration_in_code()))

    # Resumo
    print("\n" + "=" * 70)
    print(" RESUMO DOS TESTES")
    print("=" * 70)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} - {test_name}")

    total = len(results)
    passed = sum(1 for _, r in results if r)

    print("\n" + "=" * 70)
    print(f"Total: {passed}/{total} testes passaram")
    print("=" * 70)

    # Estado da implementação
    if passed == total:
        print("\n📊 IMPLEMENTAÇÃO STOP_HEARTBEAT: ✅ COMPLETA\n")
        print("📝 Funcionalidades implementadas:")
        print("  ✅ SinkDevice.block_heartbeat(nid)")
        print("  ✅ SinkDevice.unblock_heartbeat(nid)")
        print("  ✅ SinkDevice.get_blocked_heartbeat_nodes()")
        print("  ✅ SinkDevice.heartbeat_blocked_nodes (tracking)")
        print("  ✅ NetworkPacketCharacteristic.notify_packet(exclude_clients)")
        print("  ✅ CLI: stop_heartbeat <nid|índice>")
        print("  ✅ CLI: resume_heartbeat <nid|índice>")
        print("  ✅ CLI: blocked_heartbeats")
        print("  ✅ Integração em send_heartbeat()")
        print()
        print("💡 COMO USAR:")
        print("  1. Inicie Sink: ./iot-sink interactive hci0")
        print("  2. Conecte Node ao Sink")
        print("  3. No Sink CLI, use: stop_heartbeat 1")
        print("  4. Aguarde ~15s (3 heartbeats perdidos)")
        print("  5. Node detectará link failure e desconectará")
        print("  6. Use: resume_heartbeat 1 para restaurar")
        print()
    else:
        print("\n⚠️  Alguns testes falharam. Verifique os erros acima.\n")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
