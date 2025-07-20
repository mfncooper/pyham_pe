# =============================================================================
# Copyright (c) 2018-2025 Martin F N Cooper
#
# Author: Martin F N Cooper
# License: MIT License
# =============================================================================

"""
Packet Engine Application

Application layer that sits on top of the Packet Engine Client and provides a
higher level abstraction over the low level packet engine interface. Included
is higher level connection handling and monitoring support.
"""

import time

import pe
import pe.connect
import pe.monitor
import pe.handler
import pe.tocsin


class NotConnectedError(Exception):
    """
    Raised when an attempt is made to operate on the Packet Engine before
    connecting to the server or after disconnecting from it.
    """
    pass


class Application:
    """
    Top level application object for interacting with the Packet Engine.

    This is the focal point for clients using the high-level API to interact
    with the packet engine. Most client applications should use an instance
    of this class to interact with the packet engine, rather than using the
    low-level API directly.
    """
    def __init__(self):
        self._engine = None
        self._connections = None
        self._monitor = None
        self._monitor_handler = None
        self._debug_handler = None
        self._custom_handler = None

    # Application start / stop

    def start(self, host, port):
        """
        Start the packet engine client, connecting to the specified server.

        Exceptions raised by a failed attempt to connect to the server are not
        translated, and are allowed to propagate to the client, hence the
        exceptions documented here.

        :param str host: Host on which PE server is running.
        :param int port: Port to connect to on PE server.
        :raises socket.gaierror: if the server name cannot be resolved. The
            most common cause is an incorrect host name.
        :raises ConnectionRefusedError: if the server refuses the attempt to
            connect. The most common cause is an incorrect port number.
        """
        if not self._engine:
            self._start_engine(host, port)

    def stop(self):
        """
        Stop the packet engine client, and disconnect from the server.
        """
        if self._engine:
            self._stop_engine()

    # System properties

    @property
    def connected_to_server(self):
        """
        Determine whether or not the client is currently connected to the PE
        server. Readonly.

        :returns: `True` if currently connected; `False` otherwise.
        :rtype: bool
        """
        return bool(self._engine and self._engine.connected_to_server)

    @property
    def version_info(self):
        """
        Retrieve the currently cached version information. The version
        information is cached automatically when first connecting to the
        server. Readonly.

        :returns: Major and minor version information.
        :rtype: tuple(int, int)
        """
        return self._engine.version_info

    def get_port_info(self):
        """
        Retrieve the currently cached port information. The port information
        is cached automatically when first connecting to the server.

        :returns: List of available ports.
        :rtype: list[str]
        """
        return self._engine.get_cached_port_info()

    def get_port_caps(self, port):
        """
        Retrieve the currently cached port capabilities for the specified port.
        The port capabilities are cached automatically when first connecting
        to the server.

        :param int port: Port for which capabilities are to be retrieved.
        :returns: Capabilities for the specified port.
        :rtype: PortCaps
        """
        return self._engine.get_cached_port_caps(port)

    @property
    def engine(self):
        """
        Retrieve the current packet engine instance. This can be used to
        interact with the server using the lower level API. Readonly.

        :returns: Packet engine instance.
        :rtype: PacketEngine
        """
        return self._engine

    # Unproto

    def send_unproto(self, port, call_from, call_to, data, via=None):
        """
        Send an unproto (UI) message to the specified port. The message may be
        specified either as a UTF-8 string or as a byte sequence. To send to
        a destination via one or more intermediaries, specify a list of those
        intermediaries.

        :param int port: Port to which the unproto message is to be sent.
        :param str call_from: Callsign of sender.
        :param str call_to: Callsign of destination, or list of destinations
            separated by spaces.
        :param data: The message to be sent.
        :type data: str or bytes or bytearray
        :param via: List of intermediary destinations. Optional.
        :type via: list(str) or None
        :raises NotConnectedError: if not yet connected to the server.
        :raises ValueError: if the data is of an invalid type.
        """
        if not self._engine:
            raise NotConnectedError
        self._engine.send_unproto(port, call_from, call_to, data, via)

    # Connections

    def register_callsigns(self, calls):
        """
        Register one or more callsigns for use with the server. This must be
        called before the callsign is used to initiate a connection.
        Registration is not complete until the corresponding response is
        received from the server.

        :param callsign: Callsign(s) to register.
        :type callsign: str or list[str]
        """
        if isinstance(calls, str):
            self._engine.register_callsign(calls)
        else:
            for call in calls:
                self._engine.register_callsign(call)

    def is_callsign_registered(self, call):
        """
        Determine whether or not the specified callsign has already been
        registered.

        :param str callsign: Callsign to be checked.
        :returns: `True` if the callsign has been registed; `False` otherwise.
        :rtype: bool
        """
        return self._engine.is_callsign_registered(call)

    def open_connection(self, port, call_from, call_to, via=None):
        """
        Open a new connected mode session with the specified station. The
        :class:`Connection` instance returned will actually be an instance of
        the defined subclass.

        :param int port: Port to use for new connection.
        :param str call_from: Source for new connection.
        :param str call_to: Destination for new connection.
        :param via: List of intermediary destinations. Optional.
        :type via: list(str) or None
        :returns: A new connection instance.
        :rtype: Connection
        :raises NotConnectedError: if not yet connected to the server.
        """
        if not self._engine:
            raise NotConnectedError
        return self._connections.open(port, call_from, call_to, via)

    # Monitor

    def use_monitor(self, monitor):
        """
        Set the :class:`Monitor` instance to use, when monitoring is enabled.
        If this is not set, enabling monitoring will have no effect.

        :param Monitor monitor: The monitor instance to use.
        """
        self._monitor = monitor
        if self._monitor_handler:
            self._monitor_handler.monitor = monitor

    @property
    def enable_monitoring(self):
        """
        Determine or set the current state of monitoring. Setting this property
        enables or disables monitoring; setting it to its current state is
        a no-op.

        :type: bool
        """
        return self._engine.monitoring

    @enable_monitoring.setter
    def enable_monitoring(self, onoff):
        self._engine.monitoring = onoff

    # Debugging output

    @property
    def enable_debug_output(self):
        """
        Determine or set the current state of debugging output for receive
        handlers. When debug output is enabled, each response received from
        the server will be logged at the debug level.

        :type: bool
        """
        return self._debug_handler.enable_output

    @enable_debug_output.setter
    def enable_debug_output(self, onoff):
        self._debug_handler.enable_output = onoff

    # Custom receive handler

    def use_custom_handler(self, handler):
        """
        Set an application-specific receive handler. The handler will be added
        at the end of the chain created by the :class:`Application` object.
        This method must be called before calling `start()`.

        :param ReceiveHandler handler: The custom receive handler.
        """
        self._custom_handler = handler

    # Private methods

    def _start_engine(self, host, port):
        def ready(*unused):
            nonlocal started
            self._engine = engine
            self._connections = connections
            started = True
        started = False
        pe.tocsin.signal(pe.SIG_ENGINE_READY).listen(ready)
        engine = pe.PacketEngine()
        connections = pe.connect.Connections(engine)
        engine.receive_handler = self._make_receive_handler(
            connections.receive_handler)
        engine.connect_to_server(host, port)
        while not started:
            time.sleep(0.1)
        # register callsigns now?

    def _make_receive_handler(self, connection_receive_handler):
        self._debug_handler = pe.handler.DebugReceiveHandler()
        self._monitor_handler = pe.monitor.MonitorReceiveHandler()
        if self._monitor:
            self._monitor_handler.monitor = self._monitor
        handler = pe.handler.MultiReceiveHandler() \
            .add_handler(self._debug_handler) \
            .add_handler(connection_receive_handler) \
            .add_handler(self._monitor_handler)
        if self._custom_handler:
            handler.add_handler(self._custom_handler)
        return handler

    def _stop_engine(self):
        if self._engine and self._engine.connected_to_server:
            self._engine.disconnect_from_server()
        self._engine = None
