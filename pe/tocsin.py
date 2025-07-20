# =============================================================================
# Copyright (c) 2018-2025 Martin F N Cooper
#
# Author: Martin F N Cooper
# License: MIT License
# =============================================================================

"""
Tocsin

Simple signal implementation to allow decoupling of implementations by means
of emitting and listening for registered signals.

Emitter example:

.. code-block:: python

  sig = tocsin.signal('MySignal')
  sig.emit('Some MySignal-specific data')

Listener example:

.. code-block:: python

  sig = tocsin.signal('MySignal')
  sig.listen(lambda name, data: print(
    'name: {}, data: {}\\n'.format(name, data)))

-----

As can be seen from the above examples, the :py:func:`signal` function is used
to create a new signal object, or obtain an existing one with that name.

.. py:function:: signal(name)

    Create a new signal object with the specified name, or return that object
    if it already exists.

    :param str name: The name of the signal to be returned.

    :returns: A tocsin signal object.
    :rtype: :py:obj:`signal_object`

Once a signal object has been created, it may be listened for and emitted,
using the :py:func:`listen` and :py:func:`emit` functions as follows.

.. py:function:: pe.tocsin.<signal_object>.listen(cb)

    Request notification when a signal is emitted for the signal object on
    which :py:func:`listen` is invoked. The callback function should have the
    following signature:

        `callback(name, data)`

    where `name` is the name of the signal, and `data` is an arbitrary data
    object to be provided by `emit`. Since the signal name is provided, the
    same callback can be used for multiple signals.

    :param function cb: The callback function.

.. py:function:: pe.tocsin.<signal_object>.emit(data)

    Notify all listeners on the signal object, calling their callbacks with
    the signal name and the provided data. Listeners are called in the order
    in which they were created.

    :param any data: Data to be passed to the callback.


Some inspiration taken from Blinker:
  https://blinker.readthedocs.io/
"""


class _Signal:
    """
    A signal instance.

    Do not instantiaate this class; a new signal is obtained by registering
    it through the `signal` singleton instead.

    .. document private functions
    .. automethod:: listen
    """
    def __init__(self, name):
        self.name = name
        self.receivers = []

    def listen(self, fn):
        """
        Invoke the specified function whenever this signal is emitted.
        :param function fn: A function of the form ``callback(name, data)``.
        """
        self.receivers.append(fn)

    def emit(self, data=None):
        """
        this is emit
        """
        for r in self.receivers:
            r(self.name, data)


class _Signals:
    """
    The register of signals.

    Do not instantiate this class; use the `signal` singleton instead.
    """
    def __init__(self):
        self.signals = {}

    def register(self, name):
        """
        Register a new signal. Registering an already-registered signal is a
        no-op. Once registered, a signal may be listened for or emitted.

        :param str name: The name for the new signal.

        :returns: The new signal instance.
        """
        if name in self.signals:
            return self.signals[name]
        signal = _Signal(name)
        self.signals[name] = signal
        return signal


signal = _Signals().register
