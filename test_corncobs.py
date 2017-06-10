import io
import struct
import time

import pytest
from corncobs import *


def test_datapacket():
    """Unit test for datapacket class."""

    with pytest.raises(ValueError):
        DataPacket([('foobar', 'blahtype')])

    packet_def = [('cxthrottle', 'float32'), ('cxreqgear', 'uint8')]
    data = {'cxthrottle': 1.0, 'cxreqgear': 4}
    data_list = [1.0, 4]

    pck = DataPacket(packet_def, data)

    assert pck.fmt == '<fB'
    assert pck.calcsize() == 5
    assert pck.values == data

    pck = DataPacket(packet_def)
    with pytest.raises(ValueError):
        pck.pack()

    # Test that init() fails with wrong field names
    with pytest.raises(ValueError):
        pck.init({'badfield': 1.0, 'foo': 20})

    with pytest.raises(ValueError):
        pck.init([1.0, 2, 3])

    # Test that init() fails with wrong data types
    with pytest.raises(struct.error):
        pck.init({'cxthrottle': 1.0, 'cxreqgear': 4.0})
        pck.pack()

    with pytest.raises(struct.error):
        pck.init([1.0, 4.0])
        pck.pack()

    # Test init() using dict
    pck = DataPacket(packet_def)
    pck.init(data)
    assert pck.values == data

    # Test init() using list
    pck.init(data_list)
    assert pck.values == data

    # Test that init() fails with bad input
    with pytest.raises(ValueError):
        pck.init(1)

    # Test pack() and unpack()
    pck = DataPacket(packet_def, data)
    buf = pck.pack()
    data1 = pck.unpack(buf)
    assert data1 == data

    # Test set_field
    pck = DataPacket(packet_def, data)
    pck.set_field('cxreqgear', 5)
    assert pck.values == {'cxthrottle': 1.0, 'cxreqgear': 5}
    buf2 = pck.pack()
    data2 = pck.unpack(buf2)
    assert data2 == {'cxthrottle': 1.0, 'cxreqgear': 5}

    # Test that set_field fails with wrong field names
    with pytest.raises(ValueError):
        pck.set_field('badfield', 1.0)

    # Test that set_field fails with wrong datatype
    with pytest.raises(struct.error):
        pck.set_field('cxreqgear', 5.0)
        pck.pack()

    # Test that set_field fails when packet is not initialized
    pck.values = None
    with pytest.raises(ValueError):
        pck.set_field('cxreqgear', 5)

    # Test sending data directly to pack()
    pck.values = None
    buf3 = pck.pack(data)
    data3 = pck.unpack(buf3)
    assert data3 == data
    print('All tests passed!')

    # Test stream unpacking
    buf4 = io.BytesIO(buf3)
    data4 = pck.unpack_from(buf4)
    assert data4 == data


def test_streamcobs():
    """Unit test for StreamCOBS"""

    def do_test(cobs_io, test_array, test_pkt):
        # Test cobs with bytes
        if cobs_io.stream.seekable():
            cobs_io.stream.seek(0)
        cobs_io.write(test_array)

        if cobs_io.stream.seekable():
            cobs_io.stream.seek(0)
        assert cobs_io.read() == test_array

        # Test writing packets
        if cobs_io.stream.seekable(): cobs_io.stream.seek(0)
        pks = PacketCOBS(cobs_io.stream, test_pkt.definition, driver='stream')
        pks.write(test_pkt)
        if cobs_io.stream.seekable():
            cobs_io.stream.seek(0)
        out_packet = pks.read()
        assert out_packet == test_pkt

        # Test callback system
        cb_called = False
        out_cb = None

        def cb(packet):
            nonlocal cb_called, out_cb
            cb_called = True
            out_cb = packet
        cobs_io.add_listener(cb)
        cobs_io.loop_thread()

        # Wait for callback to trigger
        t0 = time.time()
        timeout = 2.0  # seconds

        cobs_io.write(test_array)
        if cobs_io.stream.seekable():
            cobs_io.stream.seek(0)  # Required for byteio stream

        while not cb_called and time.time() - t0 < timeout:
            time.sleep(0.1)

        assert out_cb == test_array

        # Test with zeros
        if cobs_io.stream.seekable():
            cobs_io.stream.seek(0)
        cobs_io.write(b'\0')
        if cobs_io.stream.seekable():
            cobs_io.stream.seek(0)
        assert cobs_io.read(max_bytes=5) == None
        assert cobs_io.read(max_bytes=5) == None

        # Stop the loop
        cobs_io.loop_stop()
        assert cobs_io.stream.closed

    test_array = bytearray(range(4))
    test_stream = io.BytesIO(bytearray(20))
    packet_def = [('cxthrottle', 'float32'), ('cxreqgear', 'uint8')]
    test_pkt = DataPacket(packet_def, [0.5, 2])

    stream_cobs = StreamCOBS(test_stream)
    do_test(stream_cobs, test_array, test_pkt)

    loop_cobs = SerialCOBS('loop://')
    do_test(loop_cobs, test_array, test_pkt)

    print('All tests passed!')
