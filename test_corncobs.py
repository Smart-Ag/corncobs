import io
import struct

import pytest
from corncobs import DataPacket, StreamCOBS

def test_datapacket():
    """Unit test for datapacket class."""
    packet_def = [('cxthrottle','float32'), ('cxreqgear','uint8')]
    pck = DataPacket(packet_def)
    assert pck.fmt == 'fB'

    data = {'cxthrottle': 1.0, 'cxreqgear': 4}

    # Test that init fails with wrong field names
    with pytest.raises(ValueError):
        pck.init({'badfield':1.0, 'foo':20})

    # Test that init() fails with wrong data types
    with pytest.raises(struct.error):
        pck.init({'cxthrottle': 1.0, 'cxreqgear': 4.0})
        pck.pack()

    # Test init()
    pck.init(data)
    assert pck.values == data

    # Test pack() and unpack()
    buf = pck.pack()
    data1 = pck.unpack(buf)
    assert data1 == data

    # Test set_field
    pck.set_field('cxreqgear', 5)
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


    # Test sending data directly to pack()
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
    test_array = bytearray(range(4))


    test_buf = bytearray(10)
    test_stream = io.BytesIO(test_buf)

    cobs_io = StreamCOBS(test_stream)
    cobs_io.write(test_array)
    test_stream.seek(0)

    out_array = cobs_io.read()
    assert out_array == test_array

    cobs_io.stream.seek(0)

    cb_called = False
    out_cb = None
    def cb(packet):
        cb_called = True
        print('in callback', cb_called, id(cb_called), packet)
        out_cb = packet

    cobs_io.add_listener(cb)
    cobs_io.loop_thread()

    import time
    while not cb_called:
        print(cb_called, id(cb_called))
        time.sleep(1.0)
        pass

    assert out_cb == test_array

    print('All tests passed!')
