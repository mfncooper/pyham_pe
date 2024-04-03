.. _user_guide:

User Guide
==========

This User Guide first introduces just a little conceptual material before
getting started with using the package itself. We will start with the lower
level material, closer to the protocol, so that you gain an understanding of
what's going on. Then we'll progressively add higher level functionality until
we have simplified the building of PE applications quite considerably.

For the easily daunted, don't worry! It really does get easier as we progress.
By the end of this User Guide, you should have a comprehensive understanding
of how to *easily* build sophisticated applications with PE.

For the impatient, you *could* jump straight to the Applications section and
work backwards from there. However, you should at least read the Concepts
section before doing that, so that you don't trip over unexpected situations
as you proceed.

For complete details of all of the classes and methods, see the
:doc:`API Reference <autoapi/index>`.


Concepts
--------

The Packet Engine (PE) protocol is request / response based, and is
asynchronous. As such, the client does not receive an immediate response to
a request, as would be the case with a regular function call. Instead, the
server will send a separate response back to the client when it is ready.

For example, the client might send a request to register a callsign with the
server. After sending the request, the client does not know whether or not
the callsign has been successfully registered or not. Only at a later time
will the client receive a response from the server indicating the result of
the original request.

A common means of handling such situations is to have the application provide
a callback function with each call to the client API, such that the callback
will be invoked when the response eventually arrives. However, this can get
unwieldy when the size of the API rises, and almost every call requires a
callback.

To handle this in a more manageable and coherent  way, PE uses a Receive
Handler. This is an "interface" that the application implements and then
provides an instance of to the engine when it is configured. The application
makes a call to the PE engine, and then the relevant method of the Receive
Handler is invoked whenever a response arrives from the server. The Receive
Handler, then, provides a focal point around which the application can manage
its responses and determine its behavior.

It is important to note that Receive Handler methods are invoked on a separate
thread created by PE. This allows the application to continue to do useful work
while responses from the server are outstanding, without requiring that the
application wait at specific points until a response is received. This is in
line with the event-driven nature of GUI or TUI applications, and simplifies
the creation of such software.

**Note:** Many, if not most, user interface frameworks, whether GUI or TUI,
require that they are updated only from the application's main thread. Thus
it is recommended that some synchronization mechanism such as Python's
``Queue`` be used to convey any updates from a receive handler to the user
interface.


Getting connected
-----------------

To get started, the first thing we need to do is create a PE instance, provide
it with our receive handler, and connect to the server.

PE does some housekeeping after the connection is established, in order to
pre-cache certain information from the server. Thus we need a means of knowing
when the engine instance is actually ready to use. This is accomplished using
a very simple signalling mechanism.

.. code-block:: python

    class MyReceiveHandler(pe.ReceiveHandler):
        # Define only the methods you need

    def ready(*unused):
        # Here the engine is ready for use

    # Listen for notification when the engine is ready to use
    pe.tocsin.signal(pe.SIG_ENGINE_READY).listen(ready)
    # Create an instance of your custom receive handler
    rh = MyReceiveHandler()
    # Create an instance of the engine, providing your receive handler
    engine = pe.PacketEngine(rh)
    # Connect to the server
    engine.connect_to_server(your_host, your_port)
    # Your ready() callback will be invoked shortly

There's no need to worry about the detailed mechanics here; when our ``ready()``
callback is invoked, we're all set, and ready to communicate with the server.

Providing our receive handler to the engine at creation time, as shown above,
is often convenient, but not required. If we needed to provide our receive
handler with the engine instance itself, for example, we can set the handler
afterwards instead, as shown below:

.. code-block:: python

    # Create an instance of the engine, without your receive handler
    engine = pe.PacketEngine()
    # Create an instance of your custom receive handler, passing it the engine
    rh = MyReceiveHandler(engine)
    # Now tell the engine about your receive handler
    engine.receive_handler = rh

Note that the receive handler *must* be set before connecting to the server.

When we're all done, we'll need to disconnect from the server.

.. code-block:: python

    engine.disconnect_from_server()


Working with the protocol
-------------------------

The core PE API provides entry points corresponding to almost all of the
request types defined by the protocol. Perhaps the simplest example is that
of sending a beacon. A beacon is sent using an UNPROTO frame in the AX.25
protocol, which is done with PE using something like:

.. code-block:: python

    engine.send_unproto(port, your_callsign, 'IDENT', 'This is a test')

where ``port`` is the AGWPE protocol port used to talk to the server (almost
always 0), and ``your_callsign`` is the source callsign. There is no
acknowledgement for UNPROTO frames, so that's all there is to it.

If we want to include one or more intermediaries in the destination path, we
can provide them using the ``via`` argument:

.. code-block:: python

    engine.send_unproto(port, your_callsign, 'IDENT', 'This is a test', ['WIDE1-1'])

In contrast to the above, which is a "send it and forget it" type invocation,
most requests sent to the server result in a response that should be handled
by our request handler. A simple example of this is requesting the server's
version information. To do this, we first ask the server to send it to us:

.. code-block:: python

    engine.ask_version()

To handle the response from the server, we implement the corresponding method
in our request handler:

.. code-block:: python

    class MyReceiveHandler(pe.ReceiveHandler):

        def version_info(self, major, minor):
            # Display or otherwise process the server's version info

Cached data
~~~~~~~~~~~

When the engine is initialized, it requests, and caches, certain information
from the server, so that the client need not deal with the asynchronous nature
of the protocol in accessing them. This cached data is made available through
read-only properties of the engine instance. Currently available information
can be accessed as follows:

.. code-block:: python

    ver_info = engine.version_info
    port_info = engine.port_info

Monitoring activity
-------------------

Monitoring of AX.25 traffic on the server is straightforward. First, our
receive handler must implement the methods corresponding to the AX.25 frame
types in which we are interested.

.. code-block:: python

    class MyReceiveHandler(pe.ReceiveHandler):

        def monitored_connected(self, port, call_from, call_to, text, data):
            # Process an AX.25 I frame

        def monitored_supervisory(self, port, call_from, call_to, text):
            # Process an AX.25 S frame

        def monitored_unproto(self, port, call_from, call_to, text, data):
            # Process an AX.25 UI frame

The server will not send monitoring data by default, so once we have set up
the engine and connected to the server, we need to enable monitoring by setting
the requisite property.

.. code-block:: python

    engine.monitoring = True

Note that we can also read this property in order to determine whether or not
monitoring is currently enabled.

The ``text`` argument to the monitoring methods contains the text content of
the packet record as defined in the AGWPE protocol. So, for example, the
``text`` argument passed for an S frame might look like::

 1:Fm KD6YAM-6 To KU6S-2 <RR R2 F=0 >[18:43:28]

If we preferred, we could work with the raw AX.25 packets as they arrive. Our
receive handler can easily provide those. We must, however, separately enable
their reception.

.. code-block:: python

    class MyReceiveHandler(pe.ReceiveHandler):

        def monitored_raw(self, port, data):
            # Process a raw AX.25 frame

    engine.raw_ax25 = True

Monitoring packets sent from the server do not, by default, include any
`unproto` packets we ourselves send using PE. In order to receive a copy of
such packets, we must implement an additional method in our receive handler.

.. code-block:: python

    class MyReceiveHandler(pe.ReceiveHandler):

        def monitored_own(self, port, call_from, call_to, pid, data):
            # Process a UI frame sent by this client


Multiple receive handlers
-------------------------

Reading through the previous section, it may have occurred to you that it might
be nice to separate your monitoring-related code from other code in your receive
handler. Or perhaps you've wondered how you could easily incorporate logging
into your code. In fact, PE enables this type of design by allowing for the
chaining of receive handlers.

Let's suppose that we want to do just this, and break out our monitoring code.
To do this, we'll define two separate receive handlers that might look like
the following.

.. code-block:: python

    class MainReceiveHandler(pe.ReceiveHandler):

        def version_info(self, major, minor):
            # Display or otherwise process the server's version info

    class MonitoringReceiveHandler(pe.ReceiveHandler):

        def monitored_connected(self, port, call_from, call_to, text, data):
            # Process an AX.25 I frame

        def monitored_supervisory(self, port, call_from, call_to, text):
            # Process an AX.25 S frame

        def monitored_unproto(self, port, call_from, call_to, text, data):
            # Process an AX.25 UI frame

Now we somehow need to tell PE that we want to use both of these. The way to
do this is to use a ``MultiReceiveHandler``.

.. code-block:: python

    rh_main = MainReceiveHandler()
    rh_mon = MonitoringReceiveHandler()
    rh = pe.handler.MultiReceiveHandler()
    rh.add_handler(rh_main)
    rh.add_handler(rh_mon)

When chaining receive handlers in this way, the methods of the receive handlers
will be invoked in the order in which the receive handlers are added.

The above works well if we might later want to remove one of the handlers you
added. However, if we're never going to remove them, which is the most common
case, we can simplify the code a little by chaining calls.

.. code-block:: python

    rh = pe.handler.MultiReceiveHandler()
        .add_handler(MainReceiveHandler())
        .add_handler(MonitoringReceiveHandler())

As we will see later, this ability to chain receive handlers using a
``MultiReceiveHandler`` is used to incorporate other PE functionality alongside
our own application's code without disrupting it.


Connected-mode sessions
-----------------------

Being able to easily work with connected-mode sessions is one of the most
attractive features of PE, and opens up a world of possible applications that
would be much more complicated to implement using other mechanisms such as
KISS or raw AX.25.

While the protocol makes it relatively straightforward to work with
connected-mode sessions, there are a few complications that need to be
handled. PE provides a higher level abstraction to simplify this. First we
will look at the basic connection functionality, close to the protocol; later
we will look at that higher level abstraction.

Before we can make any connection, though, the server must be told about any
callsign we want to use as the source of our connection. This is done by
registering the callsign(s) that we will use. As usual, we need to add to
our receive handler in order to discover whether or not our request to register
has been successful.

.. code-block:: python

    class MyReceiveHandler(pe.ReceiveHandler):

        def callsign_registered(self, callsign, success):
            # Check `success` to make sure your registration succeeded

    engine.register_callsign(your_callsign)

Once we have confirmed that our registration was successful, we can go ahead
and create a connection.

Connection fundamentals
~~~~~~~~~~~~~~~~~~~~~~~

Both connecting to and disconnecting from a remote system are incomplete until
acknowledged through our receive handler. Thus before anything else, we must
implement the corresponding methods in our receive handler.

.. code-block:: python

    class MyReceiveHandler(pe.ReceiveHandler):

        def connection_received(self, port, call_from, call_to, incoming, message):
            # Verify that your connection has been opened

        def disconnected(self, port, call_from, call_to, message):
            # Verify that your connection has been ended

There are a few important things to note in the above method signatures.

- The triple of ``port``, ``call_from`` and ``call_to`` taken together defines
  a unique connection. Multiple connections using the same triple are not
  permitted.
- All operations on the connection must be provided with the same triple in
  order to identify the connection uniquely, even if only a single connection
  is in use.
- The ``connection_received()`` method is provided with an ``incoming``
  argument. This is because this same method is invoked in response both to
  a request to open an outgoing connection *and* to an incoming request for
  a connection from a remote system.
- Both of the above methods are provided with a ``message`` argument. This is
  the text provided by the server as defined in the protocol. It is through
  this text that success or failure of your request is determined.

With these receive handler methods in place, we're now able to open and close
connections to a remote system.

.. code-block:: python

    # Open a new connection
    engine.connect(port, call_from, call_to)

    # Wait for the receive handler to be invoked before proceeding

    # At some later time, close the connection
    engine.disconnect(port, call_from, call_to)

To send data on this connection, we simply provide the data to the engine.
No acknowledgement is provided by the server in this case, so no there is no
corresponding receive handler method.

.. code-block:: python

    engine.send_data(port, call_from, call_to, data, pid)

The data provided to this method may be of type `string`, `bytes` or
`bytearray`. If a string, it will be assumed to be UTF-8 and encoded as
such. The ``pid`` argument is optional; if omitted, text data is assumed.

To receive data on the connection, we need to add another method to our
receive handler.

.. code-block:: python

    class MyReceiveHandler(pe.ReceiveHandler):

        def connected_data(self, port, call_from, call_to, pid, data):
            # Process incoming data

The incoming data will always be provided as type `bytes` or `bytearray`,
regardless of the ``pid`` value.

Simplifying connections
~~~~~~~~~~~~~~~~~~~~~~~

When only a single connection is in use at any given time, and incoming
connections are not an issue, the above mechanism is straightforward and not
too onerous. However, once we start to use multiple simultaneous outgoing
connections, and possibly incoming connections, it gets a bit harder to manage.

PE provides a higher level abstraction over connections that simplifies the
work of connection management as well as bringing a more coherent approach to
connections than is evident when working at the lower, protocol level.

Using this simplified mechanism, our connection-related code is gathered into
a dedicated class, while PE takes care of some of the underpinnings for us.

The first thing we will need to do is define a subclass of PE's ``Connection``
class. An instance of this class will be created by the PE engine whenever
one is needed, either for an outgoing or an incoming connection. (Note that
we do not need to explicitly tell PE about this class, just define it as a
subclass of PE's ``Connection`` class.)

.. code-block:: python

    class MyConnection(pe.connect.Connection):

        def __init__(self, port, call_from, call_to, incoming=False):
            super().__init__(port, call_from, call_to, incoming)
            # Now perform any initialization of your own that you might need

Before we look at the additional methods we'll need to define on this class,
let's look at how we need to set up PE to use it. As our application is
starting up, there are two things that we need to do. First, we need to
create an instance of PE's connection hub; then we need to obtain a special
PE-provided receive handler from that hub and include it in our receive
handler chain. (See `Multiple receive handlers`_ above.)

.. code-block:: python

    connections = pe.connect.Connections(engine)
    rh.add_handler(connections.receive_handler)

Now we are ready to open a new connection whenever we need one.

.. code-block:: python

    conn = connections.open(port, call_from, call_to)

The ``conn`` value returned here is an instance of our own ``Connection``
subclass, which uniquely represents the newly opened connection. With this
connection object in hand, we no longer need to carry around the port /
call_from / call_to triple to pass to each call to PE (though we can, of
course, obtain them from the connection object if we need them).

Though we now have a connection object, we do not yet know if the connection
itself is actually open. Our connection object will be notified when that
happens, and also when it is disconnected. We'll add two methods to our
``Connection`` subclass to receive these notifications.

.. code-block:: python

    class MyConnection(pe.connect.Connection):

        # ...

        def connected(self):
            # Now your connection is open

        def disconnected(self):
            # Your connection is no longer open

Now that our connection is set up, we are ready to send and receive data. This
is straightforward using the connection object.

To send data, we use the ``send_data()`` method of our connection object.

.. code-block:: python

    conn.send_data(your_data)

To receive data, we need to implement the ``data_received()`` method on our
connection class.

.. code-block:: python

    class MyConnection(pe.connect.Connection):

        # ...

        def data_received(self, pid, data):
            # Process your received data

Finally, when we are finished with the connection, we should close it.

.. code-block:: python

    conn.close()

As can be seen from the above, working with connections using this higher
level abstraction is noticeably simpler, and encapsulating our connection
functionality within its own connection class provides a cleaner way of
working with connections, particularly when we might have more than one open
at a time.

Putting it all together, our connection class will look something like the
following.

.. code-block:: python

    class MyConnection(pe.connect.Connection):

        def __init__(self, port, call_from, call_to, incoming=False):
            super().__init__(port, call_from, call_to, incoming)
            # Now perform any initialization of your own that you might need

        def connected(self):
            # Now your connection is open

        def disconnected(self):
            # Your connection is no longer open

        def data_received(self, pid, data):
            # Process your received data

and we'll work with an individual connection using the following.

.. code-block:: python

    conn = connections.open(port, call_from, call_to)
    # ...
    conn.send_data(your_data)
    # ...
    conn.close()

Incoming connections
~~~~~~~~~~~~~~~~~~~~

One final topic before we leave the discussion of connections is how incoming
connections are handled.

When PE receives an incoming request, it will call the ``query_accept()``
method on our connection class. This is a class method, so that PE can call
it before any connection instance is created. Within this method, we can
decide whether to proceed with the incoming connection, or to ignore it,
perhaps based on the callsigns involved.

.. code-block:: python

    class MyConnection(pe.connect.Connection):

        @classmethod
        def query_accept(cls, port, call_from, call_to):
            # Decide whether or not to accept this connection

Note that if we do not implement this method in our connection class, the
default is to reject all incoming connections. Thus we need take no action
unless our application specifically wants to handle incoming connections.


Applications
------------

PE has one more high level abstraction to help us build complete applications
around it. The ``Application`` class wraps up many of the components we've
been using and hides many of the "wiring" details, so that we can focus on
the core functionality of our application itself.

We start by creating an application instance, and starting it, providing the
host and port of our server.

.. code-block:: python

    app = pe.app.Application()
    app.start(server_host, server_port)

Once the ``start()`` method returns, a chain of receive handlers is in place,
and we are connected to the server. We don't need to add any more receive
handlers except under special circumstances, and we don't need to deal with
the signal that indicates that we're connected - it's all done.

Instead of interacting with a ``PacketEngine`` instance, we now interact with
our new application object. For example, all of the following are available
through the application.

.. code-block:: python

    app.send_unproto(port, call_from, call_to, data)
    # ...
    app.open_connection(port, call_from, call_to)
    # ...
    app.enable_debug_output = True
    # ...

If at some point we do need to work directly with the engine, we can obtain it
from the application.

.. code-block:: python

    engine = app.engine

Finally, when we're all done, we stop the application.

.. code-block:: python

    app.stop()

The Application chain
~~~~~~~~~~~~~~~~~~~~~

As noted above, simply creating and starting an ``Application`` instance causes
the creation of a chain of receive handlers within the application. This chain
comprises the following handlers, in this order:

- Debug receive handler, turned off by default See `Debugging`_ below.
- Connection receive handler, so that we can make use of the mechanism
  described in `Simplifying connections`_ above.
- Monitoring receive handler, so that we can receive monitoring frames from the
  server.

Note also that we no longer need to instantiate a ``Connections`` object when
building upon ``Application``, since this is taken care of for us.

Monitoring redux
~~~~~~~~~~~~~~~~

The astute reader may be wondering how they are going to receive monitoring
data in their application when they have not implemented the corresponding
methods on a receive handler. The answer is that a slightly different and
specialized monitoring "interface" is implemented instead.

.. code-block:: python

    class MyMonitor(pe.monitor.Monitor):

        def monitored_connected(self, port, call_from, call_to, text, data):
            # Process an AX.25 I frame

        def monitored_supervisory(self, port, call_from, call_to, text):
            # Process an AX.25 S frame

        def monitored_unproto(self, port, call_from, call_to, text, data):
            # Process an AX.25 UI frame

        # ... and other monitoring methods as needed

This is almost the same as implementing the receive handler methods. However,
a Monitor instance may be set on the application at any time, unlike a receive
handler, which must be set up before the application is started.

Once we have our monitor instance, we pass it to the application as follows.

.. code-block:: python

    app.use_monitor(MyMonitor())

and we can then enable or disable monitoring with:

.. code-block:: python

    app.enable_monitoring = True


Custom handlers
~~~~~~~~~~~~~~~

The built-in chain of receive handlers described above is sufficient for the
majority of applications. However, there may be situations in which we would
like to access capabilities of PE that are not provided through this chain. We
can accomplish this by creating a custom receive handler, and, if necessary,
by invoking methods of the engine directly.

As an example, let's add support to our application for printing out the most
recently heard callsigns on a port. First, we create our custom receive handler.

.. code-block:: python

    class MyCustomReceiveHandler(pe.ReceiveHandler):

        def callsign_heard_on_port(self, port, record):
            print(f'Callsign heard on {port}: {record}')

Next we tell our application to add this handler to its chain of receive
handlers. Note that, as usual, this receive handler must be set before
connecting to the server.

.. code-block:: python

    app.use_custom_handler(MyCustomReceiveHandler())

Then, once our application is connected to our server, we can ask for the
list of heard stations with:

.. code-block:: python

    app.engine.ask_callsigns_heard_on_port(0)

Our custom receive handler will be invoked once for each callsign heard, up
to a maximum of 20 times for a single request.

Debugging
---------

Quite a lot goes on in the receive handlers of an application, given that each
and every protocol response comes through them. Sometimes it is useful to see
what's going on in there, and in particular what the server is sending back to
our application. For this reason, PE includes a special receive handler that
logs every frame it receives, and we can simply include that in our chain of
receive handlers.

.. code-block:: python

    debug_handler = pe.handler.DebugReceiveHandler()
    rh.add_handler(debug_handler)

When using this receive handler, it is generally recommended that it be the
first receive handler in the chain. (This is the case when using the
``Application`` class.) That ensures that the details of each response will
be logged, potentially prior to something going wrong later in the processing
of that response.

Clearly we would not want to have to add and remove this handler to enable
logging output at different times within our application. To allow for this,
logging can be enabled and disabled at will. For example:

.. code-block:: python

    debug_handler.enable_output = False

The debug receive handler logs to a standard Python logger (``logging.Logger``)
with the name 'pe.handler' at the DEBUG logging level. You will need to enable
this in your application in order to capture the debug output.
