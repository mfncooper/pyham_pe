# =============================================================================
# Copyright (c) 2018-2025 Martin F N Cooper
#
# Author: Martin F N Cooper
# License: MIT License
# =============================================================================

"""
Packet Engine Monitor Support

Helper implementation for monitor support, including a :class:`ReceiveHandler`
and a simplified base class for monitor implementations.
"""

from pe import ReceiveHandler


class Monitor:
    """
    Facilitates monitoring of received frames.

    A subclass of this class is used to provide monitoring, taking required
    actions on received frames. An instance is provided to the monitoring
    receive handler (see :class:`MonitorReceiveHandler`) in order to effect
    monitoring.
    """

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


class MonitorReceiveHandler(ReceiveHandler):
    """
    Delegates monitoring events to a :class:`Monitor` instance.

    A receive handler that accepts a monitor implementation and delegates all
    monitoring callbacks to that implementation, eliminating the need for a
    client to extend their own receive handler for this purpose.
    """

    def __init__(self):
        self._monitor = None

    @property
    def monitor(self):
        """
        Retrieve or set the current :class:`Monitor` instance.

        :type: Monitor
        """
        return self._monitor

    @monitor.setter
    def monitor(self, mon):
        self._monitor = mon

    def monitored_connected(self, port, call_from, call_to, text, data):
        if self._monitor:
            self._monitor.monitored_connected(
                port, call_from, call_to, text, data)

    def monitored_supervisory(self, port, call_from, call_to, text):
        if self._monitor:
            self._monitor.monitored_supervisory(port, call_from, call_to, text)

    def monitored_unproto(self, port, call_from, call_to, text, data):
        if self._monitor:
            self._monitor.monitored_unproto(
                port, call_from, call_to, text, data)

    def monitored_own(self, port, call_from, call_to, text, data):
        if self._monitor:
            self._monitor.monitored_own(port, call_from, call_to, text, data)

    def monitored_raw(self, port, data):
        if self._monitor:
            self._monitor.monitored_raw(port, data)
