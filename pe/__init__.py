# =============================================================================
# Copyright (c) 2018-2025 Martin F N Cooper
#
# Author: Martin F N Cooper
# License: MIT License
# =============================================================================

"""
Packet Engine Client

Client implementation for Packet Engine, providing a simple means of calling
an engine running on a TCP/IP port. This module provides the low-level (i.e.
close to the protocol) implementation. Other modules in this package provide
higher level abstractions.

Protocol reference:
  https://www.on7lds.net/42/sites/default/files/AGWPEAPI.HTM
"""

__author__ = 'Martin F N Cooper'
__version__ = '1.1.1'

from datetime import datetime
from enum import Enum, auto
import errno
import logging
import re
import socket
import struct
import threading
from typing import NamedTuple

import pe.tocsin as tocsin

SIG_ENGINE_READY = tocsin.signal('pe_engine_ready')
SIG_SERVER_CONNECTED = tocsin.signal('pe_server_connected')
SIG_SERVER_DISCONNECTED = tocsin.signal('pe_server_disconnected')

DEF_HOST = '127.0.0.1'  # Default host
DEF_PORT = 8000         # Default port

WSAENOTSOCK = 10038  # Windows error raised when socket is closed

logger = logging.getLogger('pe')
logger.addHandler(logging.NullHandler())


class ReceiveHandler:
    """
    A no-op base class for receive handlers.

    Use of this base class is not required, but since this class provides an
    empty implementation for each frame type, using it is convenient when not
    all frame types will be supported.
    """

    def version_info(self, major, minor):
        """
        Called with the major and minor version as returned from the server.

        Corresponding frame type: 'R'

        :param int major: Major version.
        :param int minor: Minor version.
        """
        pass

    def callsign_registered(self, callsign, success):
        """
        Called with the results of an attempt to register a callsign with the
        server.

        Corresponding frame type: 'X'

        :param str callsign: Callsign being registered.
        :param bool success: `True` if registration was successful; `False`
            otherwise.
        """
        pass

    def port_info(self, info):
        """
        Called with the results of a request for information on available
        ports.

        Each returned port is a string of the form "<number>;<desc>", being
        the port number and its description, separated by a semicolon.

        Corresponding frame type: 'G'

        :param info: List of available ports.
        :type info: list[str]
        """
        pass

    def port_caps(self, port, caps):
        """
        Called with the results of a request for the capabilities of a specific
        port.

        Corresponding frame type: 'g'

        :param int port: Port for which capabilities are provided.
        :param caps: A :class:`PortCaps` instance for this port.
        :type caps: PortCaps
        """
        pass

    def callsign_heard_on_port(self, port, heard_call):
        """
        Called with the results of a request for a list of callsigns heard on
        a specified port. This method may be called multiple times for a single
        request, once for each callsign heard on the port.

        Corresponding frame type: 'H'

        :param int port: Port for which records were requested.
        :param HeardCall heard_call: Record of one callsign heard as returned
            from the server.
        """
        pass

    def frames_waiting_on_port(self, port, frames):
        """
        Called with the results of a request for the number of frames
        outstanding on a specified port.

        Corresponding frame type: 'y'

        :param int port: Port for which count is provided.
        :param int frames: The number of outstanding frames for this port.
        """
        pass

    def connection_received(self, port, call_from, call_to, incoming, message):
        """
        Called with information about a new connection, whether outgoing (i.e.
        initiated by the client) or incoming (i.e. initiated by a remote node).

        Corresponding frame type: 'C'

        :param int port: Port on which connection has been received.
        :param str call_from: Callsign of station initiating the connection.
        :param str call_to: Callsign of station receiving the connection.
        :param bool incoming: `True` if the connection was initiated by a
            remote node; `False` if it was initiated by the client.
        :param str message: Connection message. This will start with
            "\\*\\*\\* CONNECTED To" for an incoming message, or
            "\\*\\*\\* CONNECTED With" for an outgoing connection.
        """
        pass

    def connected_data(self, port, call_from, call_to, pid, data):
        """
        Called with incoming data from on ongoing connection.

        Corresponding frame type: 'D'

        :param int port: Port for ongoing connection.
        :param str call_from: Callsign of station sending the data.
        :param str call_to: Callsign of station receiving the data.
        :param int pid: The PID corresponding to the incoming data.
        :param bytearray data: The incoming data.
        """
        pass

    def disconnected(self, port, call_from, call_to, message):
        """
        Called when an ongoing connection is disconnected, whether by the
        client, the remote node, or a timeout.

        Corresponding frame type: 'd'

        :param int port: Port for ended connection.
        :param str call_from: Callsign of station that initiated the
            connection.
        :param str call_to: Callsign of station receiving the connection.
        :param str message: Disconnection message. In the case of a timeout,
            this may include the string "RETRYOUT".
        """
        pass

    def frames_waiting_on_connection(self, port, call_from, call_to, frames):
        """
        Called with the results of a request for the number of frames
        outstanding on a specified connection.

        Corresponding frame type: 'Y'

        :param int port: Port for ongoing connection.
        :param str call_from: Callsign of station initiating the connection.
        :param str call_to: Callsign of station receiving the connection.
        :param int frames: The number of outstanding frames for this
            connection.
        """
        pass

    def monitored_connected(self, port, call_from, call_to, text, data):
        """
        Called when an AX.25 Information (I) frame is received, if monitoring
        is enabled.

        Corresponding frame type: 'I'

        :param int port: Port on which frame was received.
        :param str call_from: Callsign of sending station.
        :param str call_to: Callsign of destination station.
        :param str text: Textual representation of frame, in AGWPE format.
        :param bytearray data: Data associated with the frame.
        """
        pass

    def monitored_supervisory(self, port, call_from, call_to, text):
        """
        Called when an AX.25 Supervisory (S) frame is received, if monitoring
        is enabled.

        Corresponding frame type: 'S'

        :param int port: Port on which frame was received.
        :param str call_from: Callsign of sending station.
        :param str call_to: Callsign of destination station.
        :param str text: Textual representation of frame, in AGWPE format.
        """
        pass

    def monitored_unproto(self, port, call_from, call_to, text, data):
        """
        Called when an AX.25 Unproto (U) frame is received, if monitoring
        is enabled.

        Corresponding frame type: 'U'

        :param int port: Port on which frame was received.
        :param str call_from: Callsign of sending station.
        :param str call_to: Callsign of destination station.
        :param str text: Textual representation of frame, in AGWPE format.
        :param bytearray data: Data associated with the frame.
        """
        pass

    def monitored_own(self, port, call_from, call_to, text, data):
        """
        Called when an AX.25 Unproto (U) frame has been sent by the client,
        if monitoring is enabled, allowing for confirmation of sent frames.

        Corresponding frame type: 'T'

        :param int port: Port on which frame was sent.
        :param str call_from: Callsign of sending station.
        :param str call_to: Callsign of destination station.
        :param str text: Textual representation of frame, in AGWPE format.
        :param bytearray data: Data associated with the frame.
        """
        pass

    def monitored_raw(self, port, data):
        """
        Called for all monitored frames when monitoring in raw format has been
        enabled.

        Corresponding frame type: 'K'

        :param int port: Port on which frame was received.
        :param bytearray data: Raw AX.25 frame data.
        """
        pass


_PCAPS_LEN = 12     # Port caps length
_PCAPS_FMT = '8BI'  # Format for port caps unpack


class PortCaps(NamedTuple):
    """
    Capabilities for a single port, as retrieved from the Packet Engine.

    This is a readonly structure.
    """

    baud_rate: int
    """ baud rate """
    traffic_level: int
    """ traffic level if port is in autoupdate mode """
    tx_delay: int
    """ TX delay """
    tx_tail: int
    """ TX tail """
    persist: int
    """ persistence """
    slot_time: int
    """ slot time """
    max_frame: int
    """ maximum frames """
    active_connections: int
    """ number of active connections """
    bytes_received: int
    """ number of bytes received in last 2 minutes """

    @classmethod
    def unpack(cls, buffer):
        """
        Unpack the encoded byte sequence into a new :class:`PortCaps` instance.

        :param buffer: Encoded byte sequence.
        :type buffer: bytes or bytearray
        :returns: A new PortCaps instance.
        :rtype: PortCaps
        :raises ValueError: if the length of the provided data is invalid.
        """
        if len(buffer) != _PCAPS_LEN:
            raise ValueError(
                'Invalid capabilities length: ' + str(len(buffer)))
        (baud_rate, traffic_level, tx_delay, tx_tail, persist, slot_time,
            max_frame, active_connections, bytes_received) = struct.unpack(
            _PCAPS_FMT, buffer)
        return cls(baud_rate, traffic_level, tx_delay, tx_tail, persist,
                   slot_time, max_frame, active_connections, bytes_received)


_ST_LEN = 16
_ST_FMT = 'HHxxHHHHH'


class HeardCall(NamedTuple):
    """
    Record of a callsign heard on a port.

    This is a readonly structure.
    """

    callsign: str
    """ callsign heard """
    first_heard: str
    """ when first heard, as a string """
    first_heard_ts: datetime
    """ when first heard, as a datetime instance """
    last_heard: str
    """ when last heard, as a string """
    last_heard_ts: datetime
    """when last heard, as a datetime instance"""

    @classmethod
    def unpack(cls, buffer):
        """
        Unpack the encoded byte sequence into a new :class:`HeardCall`
        instance. Note that the `datetime` values may be `None` if those
        fields were not present in the data.

        :param buffer: Encoded byte sequence.
        :type buffer: bytes or bytearray
        :returns: A new HeardCall instance.
        :rtype: HeardCall
        """
        parts = buffer.split(b'\x00', 1)

        text_parts = HeardCall._parse_text(parts[0])
        # If text parts are invalid, either it's an empty record or a bad one
        if text_parts is None:
            return None

        # There may or may not be timestamp data
        if len(parts[1]) >= _ST_LEN * 2:
            try:
                tstamps = HeardCall._parse_timestamps(parts[1])
            except (struct.error, ValueError):
                tstamps = (None, None)
        else:
            tstamps = (None, None)

        return cls(
            text_parts[0],
            text_parts[1], tstamps[0],
            text_parts[2], tstamps[1])

    @staticmethod
    def _parse_text(buffer):
        # Shortest possible string with callsign and two timestamps.
        _MIN_VIABLE_LEN = len("ID 615 925")  # noqa: N806
        try:
            text = buffer.decode('utf-8')
        except UnicodeDecodeError:
            return None
        if len(text) < _MIN_VIABLE_LEN:
            return None
        parts = text.split()
        # We need a minimum of 3 parts (callsign , first heard, last heard).
        # A timestamp may have multiple parts, but each will have the same
        # number of parts, so the total number, including callsign, must be
        # an odd number. If we have an even number, the chances are that we
        # have an empty record, where callsign is absent but timestamps are
        # present (though likely zeroed out, as in the spec).
        if len(parts) < 3 or len(parts) % 2 == 0:
            return None
        call_parts = parts[0].split('-')
        # Callsign may or may not have an SSID, but can only be one or two
        # parts. The base call must be alphanumeric.
        if len(call_parts) > 2 or not call_parts[0].isalnum():
            return None
        # If there is an SSID, it must be numeric and in the valid range.
        if len(call_parts) == 2:
            if not call_parts[1].isdecimal() or int(call_parts[1]) > 15:
                return None
        # We don't know how many pieces comprise each timestamp, but we know
        # there are two timestamps, so divide the parts in two and join each
        # set of pieces to construct the string form.
        timestamps = parts[1:]
        l_first = timestamps[:len(timestamps) // 2]
        l_last = timestamps[len(timestamps) // 2:]

        return (parts[0], ' '.join(l_first), ' '.join(l_last))

    @staticmethod
    def _parse_timestamps(buffer):
        # Three known cases:
        #  * AGWPE has extra nulls before the timestamps
        #  * ldsped < v1.18 has correct buffer size, data all nulls
        #  * ldsped >= v1.19 has correct buffer size, correct data
        expected_len = _ST_LEN * 2
        actual_len = len(buffer)
        if actual_len == expected_len:
            ts1 = struct.unpack_from(_ST_FMT, buffer, 0)
            ts2 = struct.unpack_from(_ST_FMT, buffer, _ST_LEN)
            if ts1[0] == 0 and ts2[0] == 0:
                # Looks like ldsped <= v1.18, no data
                return (None, None)
            if not ((2000 < ts1[0] < 2200) and (2000 < ts2[0] < 2200)):
                # Data looks bogus, no other options to try
                return (None, None)
        else:
            # Try AGWPE case, data at end with leading nulls
            offset = actual_len - expected_len
            ts1 = struct.unpack_from(_ST_FMT, buffer, offset)
            ts2 = struct.unpack_from(_ST_FMT, buffer, offset + _ST_LEN)
            if not ((2000 < ts1[0] < 2200) and (2000 < ts2[0] < 2200)):
                # Data looks bogus, one last option to try
                ts1 = struct.unpack_from(_ST_FMT, buffer, 0)
                ts2 = struct.unpack_from(_ST_FMT, buffer, _ST_LEN)
                if not ((2000 < ts1[0] < 2200) and (2000 < ts2[0] < 2200)):
                    # Data looks bogus, no other options to try
                    return (None, None)

        # Data looks good, convert to datetime instances
        return (
            HeardCall._systemtime_to_datetime(ts1),
            HeardCall._systemtime_to_datetime(ts2))

    @staticmethod
    def _systemtime_to_datetime(st):
        vals = list(st)
        vals[6] *= 1000  # st uses millis, dt uses micros
        return datetime(*vals)


class PacketEngine:
    """
    The Packet Engine client.

    Create an instance of this class to communicate with the Packet Engine
    server. A receive handler may be passed in as the engine is constructed,
    or later using the receive_handler property, but must be set before
    connecting to the server.
    """

    def __init__(self, handler=None):
        self._ready = False
        self._sock = None
        self._receiver = None
        self._client_handler = None
        self._active_handler = None
        self._monitor_enabled = False
        self._raw_enabled = False
        self._registered_callsigns = []
        self._version_info = None
        self._port_info = None
        self._port_caps = None
        if handler:
            self.receive_handler = handler

    def __repr__(self):
        return ("PacketEngine("
                "_ready={}, "
                "_sock={}, "
                "_receiver={}, "
                "_client_handler={}, "
                "_active_handler={}, "
                "_monitor_enabled={}, "
                "_raw_enabled={}, "
                "_registered_callsigns={}, "
                "_version_info={}, "
                "_port_info={}, "
                "_port_caps={})").format(
            self._ready,
            self._sock,
            self._receiver,
            self._client_handler,
            self._active_handler,
            self._monitor_enabled,
            self._raw_enabled,
            self._registered_callsigns,
            self._version_info,
            self._port_info,
            self._port_caps
        )

    #
    # Packet Engine client
    #

    @property
    def receive_handler(self):
        """
        Retrieve or set the current receive handler.

        :type: ReceiveHandler
        """
        return self._client_handler

    @receive_handler.setter
    def receive_handler(self, value):
        old_client_handler = self._client_handler
        self._client_handler = value
        if hasattr(self._client_handler, 'engine'):
            self._client_handler.engine = self
        if old_client_handler and self._active_handler is old_client_handler:
            self._active_handler = self._client_handler

    def connect_to_server(self, host=DEF_HOST, port=DEF_PORT):
        """
        Connect to the Packet Engine server. After setting a receive handler,
        call this before any other methods on this class.

        Note that the engine is not yet ready when this method returns; the
        caller should listen for the 'pe_engine_ready' signal to determine
        when the client is ready for use.

        Exceptions raised by a failed attempt to connect to the server are not
        translated, and are allowed to propagate to the client, hence the
        exceptions documented here.

        :param str host: Name of host to connect to.
        :param int port: Number of port to connect to.
        :raises socket.gaierror: if the server name cannot be resolved. The
            most common cause is an incorrect host name.
        :raises ConnectionRefusedError: if the server refuses the attempt to
            connect. The most common cause is an incorrect port number.
        """
        if self._ready:
            raise ValueError('Already connected')
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((host, port))
        self._receiver = _ReceiveThread(self)
        self._receiver.start()
        self._active_handler = _InitializingHandler(self, self._engine_ready)
        self._active_handler.start()
        tocsin.signal(SIG_SERVER_CONNECTED).emit()

    def _engine_ready(self):
        self._version_info = self._active_handler._version_info
        self._port_info = self._active_handler._port_info
        self._port_caps = self._active_handler._port_caps
        self._active_handler = self._client_handler
        self._ready = True
        tocsin.signal(SIG_ENGINE_READY).emit()

    def disconnect_from_server(self):
        """
        Disconnect from the Packet Engine server. Do not call other methods
        on this class after this call, except to (re)connect to a server.
        """
        self._ready = False
        self._receiver.active = False
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
            self._sock.close()
        except OSError:
            pass
        finally:
            self._sock = None
        # Reset var state to let things GC, but beware still active
        tocsin.signal(SIG_SERVER_DISCONNECTED).emit()

    @property
    def connected_to_server(self):
        """
        Determine whether or not the client is connected to the server.
        Readonly.

        :returns: `True` if connected to the server; `False` otherwise.
        :rtype: bool
        """
        return self._sock is not None

    #
    # AGWPE : Port independent methods
    #

    def register_callsign(self, callsign):  # 'X' frame
        """
        Register a callsign for use with the server. Must be called before the
        callsign is used to initiate a connection. Registration is not complete
        until the corresponding response is received from the server.

        Corresponding frame type: 'X'

        :param str callsign: Callsign to register
        """
        # Ignore if already registered
        if callsign in self._registered_callsigns:
            return
        h = _Header(0, 'X', 0, callsign, '', 0)
        self._send_frame(h)
        # Local registration happens when PE confirms via 'X' frame

    def unregister_callsign(self, callsign):  # 'x' frame
        """
        Unregister a callsign, such that it can no longer be used to initiate
        a connection. Unregistration is complete when this method returns.

        Corresponding frame type: 'x'

        :param str callsign: Callsign to unregister
        """
        # Ignore if not registered
        if callsign not in self._registered_callsigns:
            return
        h = _Header(0, 'x', 0, callsign, '', 0)
        self._send_frame(h)
        # Assume it works, since PE does not confirm
        if callsign in self._registered_callsigns:
            self._registered_callsigns.remove(callsign)

    def is_callsign_registered(self, callsign):
        """
        Determine whether or not the specified callsign has already been
        registered.

        :param str callsign: Callsign to be checked.
        :returns: `True` if the callsign has been registed; `False` otherwise.
        :rtype: bool
        """
        return callsign in self._registered_callsigns

    def ask_port_info(self):  # 'G' frame
        """
        Request information on available ports from the server. Port
        information is not returned from this method but via the `port_info()`
        method of the current receive handler, and is cached for later use.

        Corresponding frame type: 'G'
        """
        h = _Header(0, 'G', 0, '', '', 0)
        self._send_frame(h)
        # Local cache created when PE returns 'G' frame

    def get_cached_port_info(self):
        """
        Retrieve the currently cached port information.

        :returns: List of available ports.
        :rtype: list[str]
        """
        return self._port_info

    def enable_monitoring(self, onoff):  # 'm' frame
        """
        Enable or disable monitoring, per the argument. This is a no-op if the
        status of monitoring would not change.

        Corresponding frame type: 'm'

        :param bool onoff: Set to `True` to enable monitoring; set to `False`
            to disable it.
        """
        # Ignore if no change of state
        if onoff == self._monitor_enabled:
            return
        h = _Header(0, 'm', 0, '', '', 0)
        self._send_frame(h)
        self._monitor_enabled = not self._monitor_enabled

    @property
    def monitoring(self):
        """
        Query or set the current state of monitoring. Setting this property is
        equivalent to calling `enable_monitoring()`.

        :type: bool
        """
        return self._monitor_enabled

    @monitoring.setter
    def monitoring(self, value):
        self.enable_monitoring(value)

    def ask_version(self):  # 'R' frame
        """
        Request version information from the server. The information is not
        returned from this method but via the `version_info()`` method of the
        current receive handler, and is cached for later use.

        Corresponding frame type: 'R'
        """
        h = _Header(0, 'R', 0, '', '', 0)
        self._send_frame(h)
        # Local cache created when PE returns 'R' frame

    @property
    def version_info(self):
        """
        Retrieve the currently cached version information. Readonly.

        :returns: Major and minor version information.
        :rtype: tuple(int, int)
        """
        return self._version_info

    def enable_raw_ax25(self, onoff):  # 'k' frame
        """
        Enable or disable reception of frames in raw AX.25 format. When
        enabled, raw frames will be provided via the `monitored_raw()` method
        of the current receive handler. This method is a no-op if the status
        of raw frame reception would not change.

        Corresponding frame type: 'k'

        :param bool onoff: Set to `True` to enable raw frames; set to `False`
            to disable them.
        """
        # Ignore if no change of state
        if onoff == self._raw_enabled:
            return
        h = _Header(0, 'k', 0, '', '', 0)
        self._send_frame(h)
        self._raw_enabled = not self._raw_enabled

    @property
    def raw_ax25(self):
        """
        Query or set the current state of raw frame reception. Setting this
        property is equivalent to calling `enable_raw_ax25()`.

        :type: bool
        """
        return self._raw_enabled

    @raw_ax25.setter
    def raw_ax25(self, value):
        self.enable_raw_ax25(value)

    #
    # AGWPE : Port specific methods
    #

    def ask_port_caps(self, port):  # 'g' frame
        """
        Request capabilities for the specified port. Capabilities are not
        returned from this method but via the `port_caps()` method of the
        current receive handler, and are cached for later use.

        Corresponding frame type: 'g'

        :param int port: Port for which capabilities are to be retrieved.
        """
        h = _Header(port, 'g', 0, '', '', 0)
        self._send_frame(h)
        # Local cache created when PE returns 'g' frame

    def get_cached_port_caps(self, port):
        """
        Retrieve the currently cached port capabilities for the specified port.

        :param int port: Port for which capabilities are to be retrieved.
        :returns: Capabilities for the specified port.
        :rtype: PortCaps
        """
        if self._port_caps and len(self._port_caps) > port:
            return self._port_caps[port]
        return None

    def send_unproto(self, port, call_from, call_to, data, via=None):
        # 'M' or 'V' frame
        """
        Send an unproto (UI) message to the specified port. The message may be
        specified either as a string or as a byte sequence. To send to a
        destination via one or more intermediaries, specify a list of those
        intermediaries.

        Corresponding frame type: 'M' or 'V'

        :param int port: Port to which the unproto message is to be sent.
        :param str call_from: Callsign of sender.
        :param str call_to: Callsign of destination.
        :param data: The message to be sent.
        :type data: str or bytes or bytearray
        :param via: List of intermediary destinations. Optional.
        :type via: list(str) or None
        :raises ValueError: if the data is of an invalid type.
        """
        # Ensure that we have bytes
        if isinstance(data, str):
            data = data.encode('utf-8')
        elif not isinstance(data, (bytes, bytearray)):
            raise ValueError('Invalid data')
        if not via:
            # No digipeaters - simple unproto frame
            h = _Header(port, 'M', 0xF0, call_from, call_to, len(data))
            self._send_frame(h, data)
            return
        # Frame data is Via list followed by unproto data
        vias = [v.encode('utf-8') for v in via]
        fmt = 'B' + len(via) * '10s'
        frame_data = bytearray(struct.pack(fmt, len(via), *vias))
        frame_data.extend(data)
        h = _Header(port, 'V', 0xF0, call_from, call_to, len(frame_data))
        self._send_frame(h, frame_data)

    def connect(self, port, call_from, call_to, via=None, pid=None):
        # 'C', 'c' or 'v' frame
        """
        Initiate an AX.25 connected session between the source and destination
        stations. To send to a destination via one or more intermediaries,
        specify a list of those intermediaries. Confirmation of the connection
        is via the `connection_received()` method of the current receive
        handler.

        Corresponding frame type: 'C', 'c' or 'v'

        :param int port: Port on which the connection is to be made.
        :param str call_from: Callsign of source station.
        :param str call_to: Callsign of destination station.
        :param via: List of intermediary destinations. Optional.
        :type via: list(str) or None
        :param int pid: The PID to use for data on this connection. Optional.
        :raises ValueError: if the source callsign has not been registered,
            or if an invalid PID value is specified.
        """
        # Error if not registered
        if call_from not in self._registered_callsigns:
            raise ValueError('Source callsign must be registered')
        if not via:
            # No digipeaters - simple connect frame
            # For some reason, AGWPE does not support non-standard connections
            # with vias, which is why the pid handling is in here.
            if pid is None:
                pid = 0xF0
                data_kind = 'C'
            else:
                if not (0 <= pid <= 0xFF):
                    raise ValueError('Invalid pid value: {}'.format(pid))
                data_kind = 'c'
            h = _Header(port, data_kind, pid, call_from, call_to, 0)
            self._send_frame(h)
            return
        # Construct Via list
        vias = [v.encode('utf-8') for v in via]
        fmt = 'B' + len(via) * '10s'
        frame_data = struct.pack(fmt, len(via), *vias)
        h = _Header(port, 'v', 0xF0, call_from, call_to, len(frame_data))
        self._send_frame(h, frame_data)
        # Confirmation happens when PE confirms via 'C' frame

    def send_data(self, port, call_from, call_to, data, pid=None):  # 'D' frame
        """
        Send data over an open connection. The connection must have been
        previously opened with the `connect()` method.

        Corresponding frame type: 'D'

        :param int port: Port on which the data is to be sent.
        :param str call_from: Callsign of source station.
        :param str call_to: Callsign of destination station.
        :param data: The data to be sent.
        :type data: str or bytes or bytearray
        :param int pid: The PID to use for data.
        :raises ValueError: if the source callsign has not been registered,
            or if an invalid PID value is specified.
        """
        # Error if not registered
        if call_from not in self._registered_callsigns:
            raise ValueError('Callsign must be registered')
        if pid is None:
            pid = 0xF0
        elif not (0 <= pid <= 0xFF):
            raise ValueError('Invalid pid value: {}'.format(pid))
        h = _Header(port, 'D', pid, call_from, call_to, len(data))
        self._send_frame(h, data)

    def disconnect(self, port, call_from, call_to):  # 'd' frame
        """
        Close a connection previously opened with the `connect()` method.
        Confirmation of closing the connection is via the `disconnected()`
        method of the current receive handler.

        Corresponding frame type: 'd'

        :param int port: Port on which the connection was opened.
        :param str call_from: Callsign of source station.
        :param str call_to: Callsign of destination station.
        :raises ValueError: if the source callsign has not been registered.
        """
        # Error if not registered
        if call_from not in self._registered_callsigns:
            raise ValueError('Callsign must be registered')
        h = _Header(port, 'd', 0xF0, call_from, call_to, 0)
        self._send_frame(h)
        # Confirmation happens when PE confirms via 'd' frame

    def send_raw(self, port, call_from, call_to, data):  # 'K' frame
        """
        Send a raw AX.25 frame to the specified port.

        Corresponding frame type: 'K'

        :param int port: Port to which the AX.25 frame is to be sent.
        :param str call_from: Callsign of sender.
        :param str call_to: Callsign of destination.
        :param data: The AX.25 frame to be sent.
        :type data: bytes or bytearray
        """
        h = _Header(port, 'K', 0, call_from, call_to, 1 + len(data))
        buffer = bytearray()
        buffer.append(0)
        buffer.extend(data)
        self._send_frame(h, buffer)

    def ask_callsigns_heard_on_port(self, port):  # 'H' frame
        """
        Request a list of recently heard stations on the specified port.

        Corresponding frame type: 'H'

        :param int port: Port to query for heard callsigns.
        """
        h = _Header(port, 'H', 0, '', '', 0)
        self._send_frame(h)

    def ask_frames_waiting_on_port(self, port):  # 'y' frame
        """
        Request the number of outstanding frames waiting for transmission on
        the specified port.

        Corresponding frame type: 'y'

        :param int port: Port to query for outstanding frames.
        """
        h = _Header(port, 'y', 0, '', '', 0)
        self._send_frame(h)

    def ask_frames_waiting_on_connection(self, port, call_from, call_to):
        # 'Y' frame
        """
        Request the number of outstanding frames waiting for transmission on
        the connection between the specified callsigns on the specified port.

        Corresponding frame type: 'Y'

        :param int port: Port on which the connection was opened.
        :param str call_from: Callsign of source station.
        :param str call_to: Callsign of destination station.
        """
        h = _Header(port, 'Y', 0, call_from, call_to, 0)
        self._send_frame(h)

    def login(self, userid, password):  # 'P' frame
        """
        Send the user id and password to the server for authentication. There
        is no response from the server corresponding to this request, so no
        indication is available of the success or failure of authentication.

        For both fields, if a string is specified, it is assumed to be UTF-8
        and encoded accordingly. If this is not desirable, then a byte sequence
        should be specified instead.

        * Direwolf silently ignores this call.
        * ldsped accepts userid / password strings, validates them against a
          config file, and does not honor future requests if that fails.
        * AGWPE validates the input with Windows authentication.

        Corresponding frame type: 'P'

        :param userid: Id of user to validate.
        :type userid: str or bytes
        :param password: Password of user to validate.
        :type userid: str or bytes
        """
        if isinstance(userid, str):
            userid = userid.encode('utf-8')
        if isinstance(password, str):
            password = password.encode('utf-8')
        data = bytearray(255 * 2)
        data[0:len(userid)] = userid
        data[255:255 + len(password)] = password
        h = _Header(0, 'P', 0, '', '', len(data))
        self._send_frame(h, data)

    #
    # Internals
    #

    def _send_frame(self, header, data=None):
        buffer = bytearray(header.pack())
        if data:
            if isinstance(data, str):
                data = data.encode('utf-8')
            buffer.extend(data)
        blen = len(buffer)
        while True:
            sent = self._sock.send(buffer)
            blen -= sent
            if not blen:
                break
            buffer = buffer[sent:]

    def _frame_received(self, header, data):
        key = header.data_kind
        if key not in _FRAME_INFO:
            self._frame_received_error(
                header, data, 'unknown kind: {}'.format(header.data_kind))
            return
        info = _FRAME_INFO[key]
        dlen = info[1]
        if dlen == _UNDEF:
            self._frame_received_error(header, data, 'not permitted')
            return
        if dlen != _VARDATA and header.data_len != dlen:
            self._frame_received_error(
                header, data,
                'wrong data length; received {} instead of {}'.format(
                    header.data_len, dlen))
            return
        try:
            fn = getattr(self, '_frame_received_' + key)
        except AttributeError:
            self._frame_received_unsupported(header, data)
        else:
            try:
                fn(header, data)
            except Exception as e:
                msg = '{} (raised from {})'.format(str(e), str(fn))
                self._frame_received_error(header, data, msg)

    def _frame_received_error(self, header, data, msg):
        logger.error('Received frame error: {}'.format(msg))

    def _frame_received_unsupported(self, header, data):
        logger.warning(
            'Discarding unsupported frame, kind={}'.format(header.data_kind))

    def _frame_received_C(self, header, data):
        message = data.decode('utf-8')
        incoming = message.startswith('*** CONNECTED To ')
        self._active_handler.connection_received(
            header.port, header.call_from, header.call_to, incoming, message)

    def _frame_received_D(self, header, data):
        self._active_handler.connected_data(
            header.port, header.call_from, header.call_to, header.pid, data)

    def _frame_received_d(self, header, data):
        message = data.decode('utf-8')
        self._active_handler.disconnected(
            header.port, header.call_from, header.call_to, message)

    def _frame_received_G(self, header, data):
        # In some cases, AGWPE sends a too-long buffer with garbage after the
        # first zero byte, so we can't just strip trailing zero bytes.
        parts = data.split(bytearray(1), 1)[0].decode('utf-8').split(';')
        info = [x for x in parts[1:] if x]
        self._port_info = info
        self._active_handler.port_info(info)

    def _frame_received_g(self, header, data):
        caps = PortCaps.unpack(data)
        port = header.port
        if self._port_caps and 0 <= port < len(self._port_caps):
            self._port_caps[port] = caps
        self._active_handler.port_caps(header.port, caps)

    def _frame_received_H(self, header, data):
        heard_call = HeardCall.unpack(data)
        self._active_handler.callsign_heard_on_port(header.port, heard_call)

    def _frame_received_I(self, header, rawdata):
        [text, data] = self.parse_monitor_data(rawdata)
        self._active_handler.monitored_connected(
            header.port, header.call_from, header.call_to, text, data)

    def _frame_received_K(self, header, data):
        self._active_handler.monitored_raw(header.port, data)

    def _frame_received_R(self, header, data):
        major, minor = struct.unpack('H2xH2x', data)
        self._version_info = (major, minor)
        self._active_handler.version_info(major, minor)

    def _frame_received_S(self, header, rawdata):
        [text, data] = self.parse_monitor_data(rawdata)
        self._active_handler.monitored_supervisory(
            header.port, header.call_from, header.call_to, text)

    def _frame_received_T(self, header, rawdata):
        [text, data] = self.parse_monitor_data(rawdata)
        self._active_handler.monitored_own(
            header.port, header.call_from, header.call_to, text, data)

    def _frame_received_U(self, header, rawdata):
        [text, data] = self.parse_monitor_data(rawdata)
        self._active_handler.monitored_unproto(
            header.port, header.call_from, header.call_to, text, data)

    def _frame_received_X(self, header, data):
        if data[0] and header.call_from not in self._registered_callsigns:
            self._registered_callsigns.append(header.call_from)
        self._active_handler.callsign_registered(
            header.call_from, data[0] != 0)

    def _frame_received_Y(self, header, data):
        (frames,) = struct.unpack('I', data)
        self._active_handler.frames_waiting_on_connection(
            header.port, header.call_from, header.call_to, frames)

    def _frame_received_y(self, header, data):
        (frames,) = struct.unpack('I', data)
        self._active_handler.frames_waiting_on_port(header.port, frames)

    def parse_monitor_data(self, rawdata):
        pieces = rawdata.split(b'\r', 1)
        if len(pieces) != 2:
            # Invalid - just return raw data
            return [None, rawdata]
        text = pieces[0].decode('utf-8', 'replace')
        m = re.search(r' Len=(\d+) ', text)
        if not m:
            # Invalid - return all received data
            return [text, pieces[1]]
        # Correctly formed - return specified length
        return [text, pieces[1][:int(m[1])]]

    def _receive_data(self):
        buffer = bytearray()
        header = None

        while True:
            break_out = False
            try:
                data = self._sock.recv(_BUF_LEN)
            except ConnectionResetError:  # Server went away
                break_out = True
            except ConnectionAbortedError:  # Host closed connection
                break_out = True
            except OSError as e:
                if e.errno in (errno.EBADF, WSAENOTSOCK):
                    # Socket closed
                    break_out = True
                else:
                    raise
            if break_out or not data:
                return
            buffer += data
            blen = len(buffer)

            while True:
                if not header:
                    if blen < _HDR_LEN:
                        break
                    header = _Header.unpack(buffer[:_HDR_LEN])
                    buffer = buffer[_HDR_LEN:]
                    blen -= _HDR_LEN
                dlen = header.data_len
                if dlen > blen:
                    break
                self._frame_received(header, buffer[:dlen])
                buffer = buffer[dlen:]
                blen = len(buffer)
                header = None


class _ReceiveThread(threading.Thread):
    def __init__(self, engine):
        self.engine = engine
        self.active = True
        super().__init__()

    def run(self):
        while self.active:
            self.engine._receive_data()


_BUF_LEN = 4096  # Buffer length for socket i/o

_VARDATA = -1   # Variable frame data size
_UNDEF   = -2   # Frame undefined for this direction

_FRAME_INFO = {
    #        Send       Recv      Name
    'P': [ _VARDATA,   _UNDEF, 'Application Login'],
    'R': [        0,        8, 'AGWPE Version Info'],
    'G': [        0, _VARDATA, 'Port Information'],
    'g': [        0,       12, 'Port Capabilities'],
    'X': [        0,        1, 'Callsign Registration'],
    'x': [        0,   _UNDEF, 'Unregister CallSign'],
    'y': [        0,        4, 'Frames Outstanding on a Port'],
    'Y': [        0,        4, 'Frames Outstanding on a Connection'],
    'H': [        0, _VARDATA, 'Heard Stations on a Port'],
    'm': [        0,   _UNDEF, 'Enable Reception of Monitoring Frames'],
    'M': [ _VARDATA,   _UNDEF, 'Send Unproto Information'],
    'V': [ _VARDATA,   _UNDEF, 'Send Unproto VIA'],
    'C': [        0, _VARDATA, 'AX.25 Connection'],
    'v': [ _VARDATA,   _UNDEF, 'Connect an AX.25 circuit thru digipeaters'],
    'c': [        0,   _UNDEF, 'Non-Standard Connections,Connection with PID'],
    'D': [ _VARDATA, _VARDATA, 'Connected AX.25 Data'],
    'd': [        0, _VARDATA, 'Disconnect, Terminate an AX.25 Connection'],
    'U': [   _UNDEF, _VARDATA, 'Monitored Unproto Information'],
    'I': [   _UNDEF, _VARDATA, 'Monitored Connected Information'],
    'S': [   _UNDEF, _VARDATA, 'Monitored Supervisory Information'],
    'T': [   _UNDEF, _VARDATA, 'Monitoring Own Information'],
    'K': [ _VARDATA, _VARDATA, 'Monitored Information in Raw Format'],
    'k': [        0,   _UNDEF, 'Activate reception of Frames in “raw” format']
}

_HDR_LEN = 36                     # Header length
_HDR_FMT = 'BxxxBxBx10s10sIxxxx'  # Format for header pack / unpack


class _Header:
    """
    Packet Engine frame header. This header is used by all frames, whether sent
    to or received from the Packet Engine. It is always 36 bytes in length
    (when packed).
    """

    def __init__(self, port, data_kind, pid, call_from, call_to, data_len):
        self.port = port
        self.data_kind = data_kind
        self.pid = pid
        self.call_from = call_from
        self.call_to = call_to
        self.data_len = data_len

    def __repr__(self):
        return ("_Header("
                "port={}, "
                "data_kind={}, "
                "pid={}, "
                "call_from={}, "
                "call_to={}, "
                "data_len={})"
                ).format(
            self.port,
            self.data_kind,
            self.pid,
            self.call_from,
            self.call_to,
            self.data_len
        )

    def pack(self):
        call_from = bytes(self.call_from, 'utf-8', 'replace')
        call_to = bytes(self.call_to, 'utf-8', 'replace')
        return struct.pack(
            _HDR_FMT, self.port, ord(self.data_kind), self.pid,
            call_from, call_to, self.data_len)

    @classmethod
    def unpack(cls, bytes):
        if len(bytes) != _HDR_LEN:
            raise ValueError('Invalid header length: ' + str(len(bytes)))
        (port, data_kind, pid, call_from, call_to, data_len) = struct.unpack(
            _HDR_FMT, bytes)
        data_kind = chr(data_kind)
        call_from = call_from.decode('utf-8', 'replace').rstrip('\0')
        call_to = call_to.decode('utf-8', 'replace').rstrip('\0')
        return cls(port, data_kind, pid, call_from, call_to, data_len)


class _ReadyState(Enum):
    """
    State of the Packet Engine client as initialization proceeds.
    """

    NEW               = auto()
    WAITING_VERSION   = auto()
    WAITING_PORT_INFO = auto()
    WAITING_PORT_CAPS = auto()
    READY             = auto()


class _InitializingHandler(ReceiveHandler):
    """
    A special initialization handler used when connecting to the server. It
    retrieves version information, port information, and port capabilities
    at connection time so that these can be queried as soon as the server is
    ready, removing the need for the client to do that manually.
    """

    def __init__(self, engine, ready_callback):
        super().__init__()
        self._engine = engine
        self._ready_callback = ready_callback
        self._state = _ReadyState.NEW
        self._version_info = None
        self._port_info = None
        self._port_caps = []

    def start(self):
        if self._state is not _ReadyState.NEW:
            return
        self._state = _ReadyState.WAITING_VERSION
        self._engine.ask_version()

    def version_info(self, major, minor):
        if self._state is not _ReadyState.WAITING_VERSION:
            return
        self._version_info = (major, minor)
        self._state = _ReadyState.WAITING_PORT_INFO
        self._engine.ask_port_info()

    def port_info(self, info):
        if self._state is not _ReadyState.WAITING_PORT_INFO:
            return
        self._port_info = info
        if not len(info):
            self._state = _ReadyState.READY
            self._ready_callback()
        else:
            self._state = _ReadyState.WAITING_PORT_CAPS
            self._engine.ask_port_caps(0)

    def port_caps(self, port, caps):
        if self._state is not _ReadyState.WAITING_PORT_CAPS:
            return
        self._port_caps.append(caps)
        if len(self._port_caps) == len(self._port_info):
            self._state = _ReadyState.READY
            self._ready_callback()
        else:
            self._engine.ask_port_caps(port + 1)
