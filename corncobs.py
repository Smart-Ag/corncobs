__version__ = '0.4'

import io
import struct
import threading
import collections.abc as cabc

import serial
from cobs import cobs

class DataPacket(object):
    datatypes = {'float32' : 'f',
                 'float'   : 'f',
                 'uint8'   : 'B',
                 'uint16'  : 'H',
                 'uint32'  : 'I',
                 'int8'    : 'b',
                 'int16'   : 'h',
                 'int32'   : 'i',
                 'string'  : 's'}

    def __init__(self, definition, values=None):
        """
        definition : sequence of tuples
            Example: [('cxthrottle', 'float32'), ('cxreqgear','uint8')]
        """
        data_format = []
        self.fields = []
        for f_name, f_type in definition:
            if f_type not in DataPacket.datatypes:
                raise ValueError('Invalid datatype',f_type,' for field',f_name)
            data_format.append(DataPacket.datatypes[f_type])
            self.fields.append(f_name)

        self.definition = definition
        self.fmt = ''.join(data_format)

        if values is not None:
            self.init(values)
        else:
            self.values = None

    def init(self, values):
        """Initializes datapacket.

        Parameters
        ----------
        values - dict or list
        """
        if isinstance(values, cabc.Mapping):
            if all(k in self.fields for k in values):
                self.values = dict(values)
            else:
                raise ValueError('Key name mismatch')
        elif isinstance(values, cabc.Sequence):
            if len(values) == len(self.fields):
                self.values = {f_name: val for f_name,val in zip(self.fields, values)}
            else:
                raise ValueError('Number of values {} does not must match number of fields, {}'.format(len(values), len(self.fields)))
        else:
            raise ValueError('Input to init() should be either a sequence or a mapping')

    def __eq__(self, other):
        """Check equality of datapackets."""
        return self.values == other.values

    def __repr__(self):
        """Useful for printing the data packet."""
        return str(self.values)

    def copy(self):
        """Returns a copy."""
        return DataPacket(self.definition, self.values)

    def calcsize(self):
        """Returns the size of the data packet."""
        return struct.calcsize(self.fmt)

    def set_field(self, field_name, value):
        """Sets value of a specific field in the data packet.

        Parameters
        ----------
        field_name : str
            Name of the field to be set
        """
        if self.values is None:
            raise ValueError('Data packet not initialized!')
        if field_name not in self.fields:
            raise ValueError('Key name mismatch')

        self.values[field_name] = value

    def pack(self, values=None):
        """
        Packs values into byte array. Uses previously set values by default.

        Parameters
        ----------
        values - dict or list (optional)
            Specify values to be packed.
        """
        if values is not None:
            self.init(values)

        if self.values is None:
            raise ValueError('Data packet not initialized!')

        values = (self.values[f_name] for f_name in self.fields)
        return struct.pack(self.fmt, *values)

    def unpack(self, buffer):
        """
        Unpacks buffer into data packet (initializes it if necessary)

        Parameters
        ----------
        buffer - bytearray
            Buffer to be unpacked into pre-defined data structure
        """
        data = struct.unpack(self.fmt, buffer)
        if self.values is None:
            self.values = {}

        for f_name, value in zip(self.fields, data):
            self.values[f_name] = value

        return dict(self.values)

    def unpack_from(self, stream):
        """Read and unpack data from a buffered stream.

        Assumes that stream.read() will return a byte array with the packed data

        Parameters
        ----------
        stream - stream object
            Stream to read the bytes from
        """
        data = stream.read()
        return self.unpack(data)


class StreamCOBS(object):
    """Class that sends and receives data in COBS format from a stream"""
    def __init__(self, stream):
        self.stream = stream
        self.callbacks = []
        self.loop_running = False

    def _read_stream(self, nbytes):
        """
        Override this to accomodate different types of stream objects (e.g. sockets)
        """
        return self.stream.read(nbytes)

    def _write_stream(self, data):
        """
        Override this to accomodate different types of stream objects (e.g. sockets)
        """
        return self.stream.write(data)

    def write(self, data):
        """
        Writes data into stream after encoding it using COBS

        Parameters
        ----------
        data : bytearray
            Data to be encoded and written to stream

        Returns
        -------
        int
            Number of bytes written to stream
        """
        encoded_data =  b'\0' + cobs.encode(data) + b'\0'
        ret = self._write_stream(encoded_data)
        self.stream.flush()
        return ret

    def write_packet(self, packet):
        """Writes a DataPacket encoded using COBS.

        Parameters
        ----------
        packet : DataPacket
            Data packet to be written to stream
        """
        self.write(packet.pack())

    def read(self, max_bytes=255):
        """
        Reads the stream and parses COBS-encoded data

        Returns
        -------
        bytearray
            Decoded data from the stream
        """
        raw_data = bytearray()
        count = 0

        start_byte = -1
        for i in range(max_bytes-5):
            try:
                start_byte = self._read_stream(1)
            except:
                continue
            if start_byte == b'\0':
                break
        else:
            return None

        while True:
            try:
                inbyte = self._read_stream(1)
            except:
                continue
            if inbyte != b'\x00':  # Read till next null byte
                if count==max_bytes or len(inbyte) == 0:  # Stop if data stream too long
                    return None
                raw_data.append(inbyte[0])
                count+=1
                continue
            break  # Stop on null byte
        if len(raw_data) < 2:
            return None
        else:
            return cobs.decode(raw_data)

    def update(self):
        """Reads from the stream and triggers callbacks."""
        data = self.read()
        if data is not None and len(data) > 0:
            for cb in self.callbacks:
                cb(data)

    def add_listener(self, cb):
        """Adds a callback."""
        self.callbacks.append(cb)

    def loop_thread(self):
        """Start update loop in a background thread."""
        self.loop_running = True
        t = threading.Thread(target=self.loop_start, daemon=True)
        t.start()

    def loop_start(self):
        """Start update loop."""
        while self.loop_running:
            try:
                self.update()
            except Exception as e:
                print('COB Loop Error:',e)

    def loop_stop(self):
        """Stop update loop."""
        self.loop_running = False
        self.close()

    def close(self):
        """Optional close functionality."""
        if hasattr(self.stream, 'close'):
            self.stream.close()


class SerialCOBS(StreamCOBS):
    """
    A serial implementation of StreamCOBS using pySerial.

    Parameters
    ----------
    serial_port : str
        Serial port to cnect to

    All other position and keyword arguments are passed directly to pyserial
    """
    def __init__(self, serial_port, *args, **kwargs):
        self.ser = serial.serial_for_url(serial_port, *args, **kwargs)
        super().__init__(self.ser)

class TCPSocketCOBS(StreamCOBS):
    """A TCP socket implementation of StreamCOBS."""
    def _read_stream(self, nbytes):
        return self.stream.recv(nbytes)

    def _write_stream(self, data):
        return self.stream.sendall(data)
