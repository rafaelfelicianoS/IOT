#!/usr/bin/env python3
"""
Test Router Daemon - Unit tests for router daemon functionality.

Tests:
1. Router initialization
2. Session key management
3. Forwarding table learning
4. Packet forwarding logic
5. MAC recalculation
6. TTL management
7. Statistics tracking
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from common.network.router_daemon import RouterDaemon
from common.network.packet import Packet, MessageType
from common.utils.nid import NID
from common.security.crypto import calculate_hmac
import uuid

def test_initialization():
    """Test router daemon initialization."""
    print("=" * 70)
    print("TEST 1: Router Daemon Initialization")
    print("=" * 70)

    my_nid = NID(uuid.uuid4())
    router = RouterDaemon(my_nid=my_nid)

    assert router.my_nid == my_nid, "NID mismatch"
    assert router.forwarding_table is not None, "Forwarding table not initialized"
    assert router.replay_protection is not None, "Replay protection not initialized"

    print(f"✅ Router initialized with NID: {str(my_nid)[:8]}...")
    print(f"✅ Forwarding table: {type(router.forwarding_table).__name__}")
    print(f"✅ Replay protection: {type(router.replay_protection).__name__}")
    return True

def test_session_key_management():
    """Test session key set/get/remove."""
    print("\n" + "=" * 70)
    print("TEST 2: Session Key Management")
    print("=" * 70)

    router = RouterDaemon(my_nid=NID(uuid.uuid4()))

    # Set session key (exactly 32 bytes)
    session_key = b'12345678901234567890123456789012'  # 32 bytes
    router.set_session_key("uplink", session_key)

    # Verify
    assert "uplink" in router.session_keys, "Session key not set"
    assert router.session_keys["uplink"] == session_key, "Session key mismatch"

    print("✅ Session key set for uplink")

    # Remove
    router.remove_session_key("uplink")
    assert "uplink" not in router.session_keys, "Session key not removed"

    print("✅ Session key removed")
    return True

def test_forwarding_table_learning():
    """Test forwarding table learning."""
    print("\n" + "=" * 70)
    print("TEST 3: Forwarding Table Learning")
    print("=" * 70)

    router = RouterDaemon(my_nid=NID(uuid.uuid4()))

    # Learn route: source_nid → port
    source_nid = NID(uuid.uuid4())
    port_id = "uplink"

    router.forwarding_table.learn(source_nid, port_id)

    # Lookup
    result = router.forwarding_table.lookup(source_nid)
    assert result == port_id, f"Lookup failed: expected {port_id}, got {result}"

    print(f"✅ Learned: {str(source_nid)[:8]}... → {port_id}")

    # Get snapshot
    snapshot = router.get_forwarding_table_snapshot()
    assert str(source_nid) in snapshot, "Source NID not in snapshot"

    print(f"✅ Snapshot: {len(snapshot)} entries")
    return True

def test_local_delivery():
    """Test packet delivered locally."""
    print("\n" + "=" * 70)
    print("TEST 4: Local Packet Delivery")
    print("=" * 70)

    my_nid = NID(uuid.uuid4())
    router = RouterDaemon(my_nid=my_nid)

    # Register handler
    received_packet = None
    def handler(packet):
        nonlocal received_packet
        received_packet = packet

    router.register_local_handler(MessageType.DATA, handler)

    # Configure session key (must be exactly 32 bytes)
    session_key = b'12345678901234567890123456789012'  # 32 bytes
    router.set_session_key("uplink", session_key)

    # Create packet destined for us
    packet = Packet.create(
        source=NID(uuid.uuid4()),
        destination=my_nid,
        msg_type=MessageType.DATA,
        payload=b"Hello local!",
        sequence=1
    )

    # Calculate MAC
    mac_data = (
        packet.source.to_bytes() +
        packet.destination.to_bytes() +
        bytes([packet.msg_type, packet.ttl]) +
        packet.sequence.to_bytes(4, 'big') +
        packet.payload
    )
    packet.mac = calculate_hmac(mac_data, session_key)

    # Receive packet
    router.receive_packet("uplink", packet.to_bytes())

    # Verify handler was called
    assert received_packet is not None, "Handler not called"
    assert received_packet.payload == b"Hello local!", "Payload mismatch"

    print("✅ Packet delivered to local handler")
    print(f"   Payload: {received_packet.payload.decode()}")

    # Check stats
    stats = router.get_stats()
    assert stats['delivered'] == 1, "Delivery count incorrect"

    print(f"✅ Statistics: {stats}")
    return True

def test_packet_forwarding():
    """Test packet forwarding to another hop."""
    print("\n" + "=" * 70)
    print("TEST 5: Packet Forwarding")
    print("=" * 70)

    my_nid = NID(uuid.uuid4())
    router = RouterDaemon(my_nid=my_nid)

    # Setup: two ports with session keys (exactly 32 bytes each)
    uplink_key = b'UPLINK__123456789012345678901234'  # 32 bytes
    downlink_key = b'DOWNLINK123456789012345678901234'  # 32 bytes

    router.set_session_key("uplink", uplink_key)
    router.set_session_key("downlink", downlink_key)

    # Learn route: destination → uplink
    dest_nid = NID(uuid.uuid4())
    router.forwarding_table.learn(dest_nid, "uplink")

    # Track sent packets
    sent_packets = []
    def send_callback(port_id, packet_bytes):
        sent_packets.append((port_id, packet_bytes))
        return True

    router.set_send_callback(send_callback)

    # Create packet from downlink destined for dest_nid
    source_nid = NID(uuid.uuid4())
    packet = Packet.create(
        source=source_nid,
        destination=dest_nid,
        msg_type=MessageType.DATA,
        payload=b"Forward me!",
        sequence=1,
        ttl=8
    )

    # Calculate MAC with downlink key
    mac_data = (
        packet.source.to_bytes() +
        packet.destination.to_bytes() +
        bytes([packet.msg_type, packet.ttl]) +
        packet.sequence.to_bytes(4, 'big') +
        packet.payload
    )
    packet.mac = calculate_hmac(mac_data, downlink_key)

    # Receive from downlink (should forward to uplink)
    router.receive_packet("downlink", packet.to_bytes())

    # Verify packet was forwarded
    assert len(sent_packets) == 1, f"Expected 1 forwarded packet, got {len(sent_packets)}"

    port_id, packet_bytes = sent_packets[0]
    assert port_id == "uplink", f"Forwarded to wrong port: {port_id}"

    # Parse forwarded packet
    forwarded = Packet.from_bytes(packet_bytes)

    # Verify TTL was decremented
    assert forwarded.ttl == 7, f"TTL not decremented: {forwarded.ttl}"

    # Verify payload unchanged
    assert forwarded.payload == b"Forward me!", "Payload changed during forward"

    print("✅ Packet forwarded: downlink → uplink")
    print(f"   TTL: 8 → {forwarded.ttl}")
    print(f"   Payload: {forwarded.payload.decode()}")

    # Verify forwarding table learned source route
    learned_port = router.forwarding_table.lookup(source_nid)
    assert learned_port == "downlink", "Source route not learned"

    print(f"✅ Learned return route: {str(source_nid)[:8]}... → downlink")

    # Check stats
    stats = router.get_stats()
    assert stats['routed'] == 1, "Routed count incorrect"

    print(f"✅ Statistics: {stats}")
    return True

def test_ttl_expiration():
    """Test TTL expiration (packet dropped)."""
    print("\n" + "=" * 70)
    print("TEST 6: TTL Expiration")
    print("=" * 70)

    my_nid = NID(uuid.uuid4())
    router = RouterDaemon(my_nid=my_nid)

    # Configure (must be exactly 32 bytes)
    session_key = b'DOWNLINK123456789012345678901234'  # Exactly 32
    router.set_session_key("downlink", session_key)

    dest_nid = NID(uuid.uuid4())
    router.forwarding_table.learn(dest_nid, "uplink")

    sent_packets = []
    router.set_send_callback(lambda p, b: sent_packets.append((p, b)) or True)

    # Create packet with TTL=1
    packet = Packet.create(
        source=NID(uuid.uuid4()),
        destination=dest_nid,
        msg_type=MessageType.DATA,
        payload=b"Should be dropped",
        sequence=1,
        ttl=1  # Will become 0 after decrement
    )

    # Calculate MAC
    mac_data = (
        packet.source.to_bytes() +
        packet.destination.to_bytes() +
        bytes([packet.msg_type, packet.ttl]) +
        packet.sequence.to_bytes(4, 'big') +
        packet.payload
    )
    packet.mac = calculate_hmac(mac_data, session_key)

    # Receive packet
    router.receive_packet("downlink", packet.to_bytes())

    # Verify packet was NOT forwarded
    assert len(sent_packets) == 0, "Packet with TTL=1 was forwarded (should be dropped)"

    print("✅ Packet with TTL=1 dropped (not forwarded)")

    # Check stats
    stats = router.get_stats()
    assert stats['dropped'] >= 1, "Dropped count incorrect"

    print(f"✅ Statistics: {stats}")
    return True

def test_statistics():
    """Test statistics tracking."""
    print("\n" + "=" * 70)
    print("TEST 7: Statistics Tracking")
    print("=" * 70)

    my_nid = NID(uuid.uuid4())
    router = RouterDaemon(my_nid=my_nid)

    # Initial stats
    stats = router.get_stats()
    assert stats['routed'] == 0, "Initial routed != 0"
    assert stats['delivered'] == 0, "Initial delivered != 0"
    assert stats['dropped'] == 0, "Initial dropped != 0"
    assert stats['total'] == 0, "Initial total != 0"

    print(f"✅ Initial stats: {stats}")

    # Simulate some activity
    router.packets_routed = 10
    router.packets_delivered_locally = 5
    router.packets_dropped = 2

    stats = router.get_stats()
    assert stats['routed'] == 10, "Routed count wrong"
    assert stats['delivered'] == 5, "Delivered count wrong"
    assert stats['dropped'] == 2, "Dropped count wrong"
    assert stats['total'] == 17, "Total count wrong"

    print(f"✅ Updated stats: {stats}")
    return True

def main():
    """Run all tests."""
    print("\n" + "🔀" * 35)
    print("      ROUTER DAEMON UNIT TESTS")
    print("🔀" * 35 + "\n")

    tests = [
        ("Initialization", test_initialization),
        ("Session Key Management", test_session_key_management),
        ("Forwarding Table Learning", test_forwarding_table_learning),
        ("Local Delivery", test_local_delivery),
        ("Packet Forwarding", test_packet_forwarding),
        ("TTL Expiration", test_ttl_expiration),
        ("Statistics Tracking", test_statistics),
        ("HEARTBEAT with DEFAULT_HMAC_KEY", test_heartbeat_with_default_hmac_key),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"\n❌ FAILED: {name}")
            print(f"   Reason: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ ERROR: {name}")
            print(f"   Exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(" SUMMARY")
    print("=" * 70)
    print(f"✅ Passed: {passed}/{len(tests)}")
    if failed > 0:
        print(f"❌ Failed: {failed}/{len(tests)}")
    print("=" * 70)

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Router Daemon is functional.\n")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review output above.\n")
        return 1

def test_heartbeat_with_default_hmac_key():
    """Test that HEARTBEAT packets use DEFAULT_HMAC_KEY for MAC verification."""
    print("\n" + "="*70)
    print("TEST 8: HEARTBEAT packets with DEFAULT_HMAC_KEY")
    print("="*70)

    from common.security.crypto import DEFAULT_HMAC_KEY
    from common.protocol.heartbeat import create_heartbeat_packet

    # Setup
    sink_nid = NID(uuid.uuid4())
    node_nid = NID(uuid.uuid4())
    router = RouterDaemon(my_nid=node_nid)

    # Configure session key (ECDH key) for uplink
    ecdh_session_key = b'12345678901234567890123456789012'  # 32 bytes
    router.set_session_key("uplink", ecdh_session_key)

    # Track received heartbeats
    received_heartbeats = []
    def heartbeat_handler(packet):
        received_heartbeats.append(packet)

    router.register_local_handler(MessageType.HEARTBEAT, heartbeat_handler)

    # Create heartbeat packet (simulating Sink sending it)
    # This uses DEFAULT_HMAC_KEY internally
    heartbeat_packet = create_heartbeat_packet(
        sink_nid=sink_nid,
        cert_manager=None,  # No signature for this test
        broadcast_nid=sink_nid,
        sequence=42,
    )

    print(f"📤 Created heartbeat packet:")
    print(f"   Source: {sink_nid}")
    print(f"   Dest: {sink_nid} (broadcast)")
    print(f"   Seq: 42")
    print(f"   MAC uses: DEFAULT_HMAC_KEY")

    # Router receives heartbeat from uplink
    # Should verify MAC with DEFAULT_HMAC_KEY (NOT session key)
    router.receive_packet("uplink", heartbeat_packet.to_bytes())

    # Verify heartbeat was delivered locally
    assert len(received_heartbeats) == 1, f"Expected 1 heartbeat, got {len(received_heartbeats)}"

    received = received_heartbeats[0]
    assert received.source == sink_nid, "Source mismatch"
    assert received.msg_type == MessageType.HEARTBEAT, "Type mismatch"
    assert received.sequence == 42, "Sequence mismatch"

    print(f"✅ Heartbeat received and verified with DEFAULT_HMAC_KEY")
    print(f"   (despite having ECDH session key configured)")

    # Verify statistics
    stats = router.get_stats()
    assert stats['delivered'] == 1, f"Expected 1 delivered, got {stats['delivered']}"
    assert stats['dropped'] == 0, f"Expected 0 dropped, got {stats['dropped']}"

    print("✅ PASS - HEARTBEAT packets correctly use DEFAULT_HMAC_KEY")
    return True


if __name__ == "__main__":
    sys.exit(main())
