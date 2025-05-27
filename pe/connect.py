# =============================================================================
# Copyright (c) 2019-2025 Martin F N Cooper
#
# Author: Martin F N Cooper
# License: MIT License
# =============================================================================

"""
Packet Engine Connection Handling

Connection handling layer that sits on top of the Packet Engine Client and
provides a simplified connection-oriented interface, avoiding the need for
direct interaction with the packet engine interface.

To use this layer, the following steps are required:

* Define a subclass of the :class:`Connection` base class that
  will handle interactions with a connection.
* Create an instance of the :class:`Connections` class that will manage all
  of the connections for the specified Packet Engine instance.
* Obtain the request handler from the :class:`Connections` instance and add
  it to the chain of request handlers for your engine instance.
* Use the :py:func:`open` function of your :class:`Connections` instance to
  create new connected-mode connections.
"""

from enum import Enum, auto

from pe import ReceiveHandler


class ConnectionClassNotFoundError(Exception):
    """
    Raised when an attempt is made to open a connection but no subclass of
    :class:`Connection` has been defined.
    """
    pass


class ConnectionError(Exception):
    """
    Raised when a connection attempt fails or a connection is terminated
    unexpectedly.
    """
    pass


class ConnectionState(Enum):
    """
    The current state of a connection.

    This is updated as the state progresses, from initiation through
    connection to completion.
    """
    CONNECTING    = auto()
    """ Attempting to connect """
    CONNECTED     = auto()
    """ Successfully connected """
    DISCONNECTING = auto()
    """ Attempting to disconnect """
    DISCONNECTED  = auto()
    """ Not yet, or no longer, connected """
    TIMEDOUT      = auto()
    """ Connection attempt timed out """


class Connection:
    """
    An AX.25 connected session between two stations.

    This may be a connection initiated by the client, or an incoming
    connection from a remote station.

    This is a base class that is intended to be subclassed so that action may
    be taken on events such as connection status changes or receipt of
    incoming data.

    :param int port: Port on which the connection is established.
    :param str call_from: Callsign of station initiating the connection.
    :param str call_to: Callsign of station receiving the connection.
    :param bool incoming: `True` if the connection was initiated by the remote
        station; `False` otherwise.
    """
    _connection_cls = None

    def __init__(self, port, call_from, call_to, incoming=False):
        self._port = port
        self._call_from = call_from
        self._call_to = call_to
        self._incoming = incoming
        self._state = ConnectionState.DISCONNECTED
        self._engine = None
        self._key = None

    def __init_subclass__(cls, **kwargs):
        """
        Auto-register the client-defined subclass of this class. If the client
        defines multiple levels of subclass, the topmost definition "wins",
        and the expected class will be instantiated.
        """
        super().__init_subclass__(**kwargs)
        Connection._connection_cls = cls

    @property
    def port(self):
        """
        Port on which the connection was established. Readonly.

        :returns: Port for this connection.
        :rtype: int
        """
        return self._port

    @property
    def call_from(self):
        """
        Callsign of station initiating the connection. Readonly.

        :returns: Callsign of initiating station.
        :rtype: str
        """
        return self._call_from

    @property
    def call_to(self):
        """
        Callsign of station receiving the connection. Readonly.

        :returns: Callsign of receiving station.
        :rtype: str
        """
        return self._call_to

    @property
    def incoming(self):
        """
        Whether or not the connection is incoming, i.e. initiated by a remote
        station. Readonly.

        :returns: `True` if the connection was initiated by the remote station;
            `False` otherwise.
        :rtype: bool
        """
        return self._incoming

    @property
    def state(self):
        """
        Current state of the connection. Readonly.

        :returns: Connection state.
        :rtype: ConnectionState
        """
        return self._state

    @classmethod
    def query_accept(cls, port, call_from, call_to):
        """
        Determine whether or not an incoming connection on the specified port,
        from the specified source and to the specified destination, should be
        accepted.

        The default implementation always returns `False`, but this method may
        be overridden in a subclass in order to control which incoming
        connections are accepted.

        :param int port: Port for incoming connection.
        :param str call_from: Callsign of station initiating the connection.
        :param str call_to: Callsign of station receiving the connection.
        :returns: `True` if the connection should be accepted; `False`
            otherwise.
        :rtype: bool
        """
        return False

    def send_data(self, data):
        """
        Send data on the currently open connection.

        :param data: Data to be sent.
        :type data: bytes or bytearray
        """
        if self.incoming:
            self._engine.send_data(
                self._port, self._call_to, self._call_from, data)
        else:
            self._engine.send_data(
                self._port, self._call_from, self._call_to, data)

    def close(self):
        """
        Close the currently open connection.
        """
        self._state = ConnectionState.DISCONNECTING
        if self.incoming:
            self._engine.disconnect(self._port, self._call_to, self._call_from)
        else:
            self._engine.disconnect(self._port, self._call_from, self._call_to)

    # Methods for subclasses to implement

    def connected(self):
        """
        Called when a connection has been successfully opened. This method
        should be implemented by a subclass in order to detect connection
        initiation and act on it appropriately.
        """
        pass

    def disconnected(self):
        """
        Called when a connection has been closed. This method should be
        implemented by a subclass in order to detect connection completion
        and act on it appropriately.
        """
        pass

    def data_received(self, pid, data):
        """
        Called when data has been received on an open connection. This method
        should be implemented by a subclass in order to receive and process
        incoming data.

        :param int pid: The PID corresponding to the incoming data.
        :param bytearray data: The incoming data.
        """
        pass


class _ConnectionMap:
    def __init__(self):
        self._connections = {}

    def _make_key(self, port, call_from, call_to):
        calls = sorted([call_from, call_to])
        return '{}:{}:{}'.format(port, *calls)

    def find(self, port, call_from, call_to):
        key = self._make_key(port, call_from, call_to)
        return self._connections[key] if key in self._connections else None

    def add(self, conn):
        key = self._make_key(conn._port, conn._call_from, conn._call_to)
        if key in self._connections:
            raise ValueError('Connection already exists')
        conn._key = key
        self._connections[key] = conn
        return key

    def remove(self, conn):
        if conn._key is None or conn._key not in self._connections:
            raise ValueError('Connection does not exist')
        del self._connections[conn._key]
        conn._key = None


class Connections:
    """
    Focal point for all connected-mode connections.

    Create an instance of this class to work with connected sessions for the
    provided packet engine instance. The corresponding request handler must
    be added to the engine's request handler chain. An instance of your defined
    :class:`Connection` subclass will be created for each connection.

    :param engine: Packet engine client instance.
    :type engine: PacketEngine
    """
    def __init__(self, engine):
        self._engine = engine
        self._connection_map = _ConnectionMap()
        self._receive_handler = None

    @property
    def receive_handler(self):
        """
        Retrieve the receive handler that will be used to create and invoke
        methods on connection instances.

        :type: ReceiveHandler
        """
        if not self._receive_handler:
            self._receive_handler = _ConnectionReceiveHandler(
                self._engine, self._connection_map)
        return self._receive_handler

    def open(self, port, call_from, call_to, via=None):
        """
        Open a new connected-mode connection.

        :param int port: Port to use for new connection.
        :param str call_from: Source for new connection.
        :param str call_to: Destination for new connection.
        :param via: List of intermediary destinations. Optional.
        :type via: list(str) or None
        :returns: A new :class:`Connection` instance.
        :rtype: Connection
        :raises ConnectionClassNotFoundError: when no :class:`Connection`
            subclass has been defined.
        """
        if not Connection._connection_cls:
            raise ConnectionClassNotFoundError()
        conn = Connection._connection_cls(port, call_from, call_to)
        conn._engine = self._engine
        self._connection_map.add(conn)
        conn._state = ConnectionState.CONNECTING
        self._engine.connect(port, call_from, call_to, via)
        return conn


class _ConnectionReceiveHandler(ReceiveHandler):
    """
    Receive handler that processes responses related to connected sessions.

    It invokes the :class:`Connection` methods as appropriate. This must be
    included in the engine's request handler chain so that connections will
    be managed on behalf of the client.
    """
    def __init__(self, engine, connection_map):
        self._engine = engine
        self._connection_map = connection_map

    def connection_received(self, port, call_from, call_to, incoming, message):
        conn = self._connection_map.find(port, call_from, call_to)
        if incoming:
            if conn:
                return
            if not Connection._connection_cls.query_accept(
                    port, call_from, call_to):
                return
            conn = Connection._connection_cls(
                port, call_from, call_to, incoming)
            conn._engine = self._engine  # Needed in connection object?
            conn._key = self._connection_map.add(conn)
            conn._state = ConnectionState.CONNECTED
            conn.connected()
        else:
            if not conn:
                return
            conn._state = ConnectionState.CONNECTED
            conn.connected()

    def connected_data(self, port, call_from, call_to, pid, data):
        conn = self._connection_map.find(port, call_from, call_to)
        if conn:
            conn.data_received(pid, data)

    def disconnected(self, port, call_from, call_to, message):
        conn = self._connection_map.find(port, call_from, call_to)
        if conn:
            if 'RETRYOUT' in message:
                conn._state = ConnectionState.TIMEDOUT
            else:
                conn._state = ConnectionState.DISCONNECTED
            self._connection_map.remove(conn)
            conn.disconnected()
