# =============================================================================
# Copyright (c) 2018-2025 Martin F N Cooper
#
# Author: Martin F N Cooper
# License: MIT License
# =============================================================================

"""
Packet Engine Receive Handler Helpers

Helper implementations for :class:`ReceiveHandler` that assist in building
chains of more specialized helpers, and in debugging said chains.
"""

import logging

from pe import ReceiveHandler


logger = logging.getLogger('pe.handler')


class MultiReceiveHandler(ReceiveHandler):
    """
    A receive handler that builds a chain of receive handlers.

    Each receive handler is called in turn when the corresponding method is
    called. Handlers are called in the order in which they are added.
    """

    #
    # MultiReceiveHandler methods
    #

    def __init__(self):
        self._handlers = []

    def add_handler(self, handler):
        """
        Add a new :class:`ReceiveHandler` to the end of the current chain of
        handlers. This method returns the :class:`MultiReceiveHandler`, thus
        allowing for multiple handlers to be added through chaining of calls
        to this method.

        :param handler: ReceiveHandler instance to add.
        :type handler: ReceiveHandler
        :returns: This :class:`MultiReceiveHandler` instance.
        :rtype: MultiReceiveHandler
        """
        if handler not in self._handlers:
            self._handlers.append(handler)
        return self

    def remove_handler(self, handler):
        """
        Remove the specified handler from the current chain of handlers. This
        method returns the :class:`MultiReceiveHandler`, thus allowing for
        multiple handlers to be removed through chaining of calls to this
        method.

        :param handler: ReceiveHandler instance to remove.
        :type handler: ReceiveHandler
        :returns: This :class:`MultiReceiveHandler` instance.
        :rtype: MultiReceiveHandler
        """
        if handler in self._handlers:
            self._handlers.remove(handler)
        return self

    #
    # ReceiveHandler methods
    #

    def version_info(self, major, minor):
        for h in self._handlers:
            h.version_info(major, minor)

    def callsign_registered(self, callsign, success):
        for h in self._handlers:
            h.callsign_registered(callsign, success)

    def port_info(self, info):
        for h in self._handlers:
            h.port_info(info)

    def port_caps(self, port, caps):
        for h in self._handlers:
            h.port_caps(port, caps)

    def callsign_heard_on_port(self, port, heard_call):
        for h in self._handlers:
            h.callsign_heard_on_port(port, heard_call)

    def frames_waiting_on_port(self, port, frames):
        for h in self._handlers:
            h.frames_waiting_on_port(port, frames)

    def connection_received(self, port, call_from, call_to, incoming, message):
        for h in self._handlers:
            h.connection_received(port, call_from, call_to, incoming, message)

    def connected_data(self, port, call_from, call_to, pid, data):
        for h in self._handlers:
            h.connected_data(port, call_from, call_to, pid, data)

    def disconnected(self, port, call_from, call_to, message):
        for h in self._handlers:
            h.disconnected(port, call_from, call_to, message)

    def frames_waiting_on_connection(self, port, call_from, call_to, frames):
        for h in self._handlers:
            h.frames_waiting_on_connection(port, call_from, call_to, frames)

    def monitored_connected(self, port, call_from, call_to, text, data):
        for h in self._handlers:
            h.monitored_connected(port, call_from, call_to, text, data)

    def monitored_supervisory(self, port, call_from, call_to, text):
        for h in self._handlers:
            h.monitored_supervisory(port, call_from, call_to, text)

    def monitored_unproto(self, port, call_from, call_to, text, data):
        for h in self._handlers:
            h.monitored_unproto(port, call_from, call_to, text, data)

    def monitored_own(self, port, call_from, call_to, text, data):
        for h in self._handlers:
            h.monitored_own(port, call_from, call_to, text, data)

    def monitored_raw(self, port, data):
        for h in self._handlers:
            h.monitored_raw(port, data)


class DebugReceiveHandler(ReceiveHandler):
    """
    A receive handler that logs each method call along with its arguments.

    Logging is at the DEBUG level, and may be enabled and disabled by means
    of the `enable_output` property.
    """

    #
    # DebugReceiveHandler methods
    #

    def __init__(self):
        self._enable_output = False

    @property
    def enable_output(self):
        """
        Query or set the current state of debug logging output.

        :type: bool
        """
        return self._enable_output

    @enable_output.setter
    def enable_output(self, onoff):
        self._enable_output = onoff

    def _debug_out(self, s):
        if self._enable_output:
            logger.debug(s)

    #
    # ReceiveHandler methods
    #

    def version_info(self, major, minor):
        self._debug_out('version_info:\n  major: {}\n  minor: {}\n'.format(
            major, minor))

    def callsign_registered(self, callsign, success):
        self._debug_out(
            ('callsign_registered:\n  callsign: {}\n'
             '  success: {}\n').format(
                callsign, success))

    def port_info(self, info):
        self._debug_out('port_info:\n  info: {}\n'.format(info))

    def port_caps(self, port, caps):
        self._debug_out('port_caps:\n  port: {}\n  caps: {}\n'.format(
            port, caps))

    def callsign_heard_on_port(self, port, heard_call):
        self._debug_out(
            'callsign_heard_on_port:\n  port: {}\n  heard: {}\n'.format(
                port, heard_call))

    def frames_waiting_on_port(self, port, frames):
        self._debug_out(
            'frames_waiting_on_port:\n  port: {}\n  frames: {}\n'.format(
                port, frames))

    def connection_received(self, port, call_from, call_to, incoming, message):
        self._debug_out(
            ('connection_received:\n  port: {}\n  call_from: {}\n'
             '  call_to: {}\n  incoming: {}\n  message: {}\n').format(
                port, call_from, call_to, incoming, message))

    def connected_data(self, port, call_from, call_to, pid, data):
        self._debug_out(
            ('connected_data:\n  port: {}\n  call_from: {}\n'
             '  call_to: {}\n  pid: {:#02x}\n  data: {}\n').format(
                port, call_from, call_to, pid, data))

    def disconnected(self, port, call_from, call_to, message):
        self._debug_out(
            ('disconnected:\n  port: {}\n  call_from: {}\n'
             '  call_to: {}\n  message: {}\n').format(
                port, call_from, call_to, message))

    def frames_waiting_on_connection(self, port, call_from, call_to, frames):
        self._debug_out(
            ('frames_waiting_on_connection:\n  port: {}\n  call_from: {}\n'
             '  call_to: {}\n  frames: {}\n').format(
                port, call_from, call_to, frames))

    def monitored_connected(self, port, call_from, call_to, text, data):
        self._debug_out(
            ('monitored_connected:\n  port: {}\n  call_from: {}\n'
             '  call_to: {}\n  text: {}\n data: {}\n').format(
                port, call_from, call_to, text, data))

    def monitored_supervisory(self, port, call_from, call_to, text):
        self._debug_out(
            ('monitored_supervisory:\n  port: {}\n  call_from: {}\n'
             '  call_to: {}\n  text: {}\n').format(
                port, call_from, call_to, text))

    def monitored_unproto(self, port, call_from, call_to, text, data):
        self._debug_out(
            ('monitored_unproto:\n  port: {}\n  call_from: {}\n'
             '  call_to: {}\n  text: {}\n data: {}\n').format(
                port, call_from, call_to, text, data))

    def monitored_own(self, port, call_from, call_to, text, data):
        self._debug_out(
            ('monitored_own:\n  port: {}\n  call_from: {}\n'
             '  call_to: {}\n  text: {}\n  data: {}\n').format(
                port, call_from, call_to, text, data))

    def monitored_raw(self, port, data):
        self._debug_out('monitored_raw:\n  port: {}\n  data: {}\n'.format(
            port, data))
