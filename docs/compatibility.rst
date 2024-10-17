.. _compatibility:

Compatibility
=============

The PyHam PE package supports the full AGWPE protocol. However, not all servers
that support the AGWPE protocol include support for all facets of the protocol,
and not all of them support all facets in the same way. Below are some of the
documented or observed differences between the AGWPE protocol specification and
the servers that PE has been tested against.

In general, where a server does not support a particular feature, the behavior
is such that a request associated with that feature will be silently ignored.

The information on this page is current as of the following versions of the
most popular AGWPE servers:

- Direwolf v1.7
- ldsped v1.19
- AGWPE v2013.415
- QtSoundModem 0.0.0.73


Protocol features
-----------------

Note that the table below reflects only facets of the protocol that are not
fully supported by all servers. All other facets are supported by all servers.

.. list-table:: AGWPE Server Compatibility
   :header-rows: 1

   * - Feature
     - Direwolf
     - ldsped
     - AGWPE
     - QtSoundModem
   * - Application login
     - No
     - Yes
     - Yes
     - No
   * - Port capabilities
     - Yes [#]_
     - Yes
     - Yes
     - Yes
   * - Heard stations
     - No
     - Yes [#]_
     - Yes
     - No
   * - Frames waiting on port
     - Yes
     - No
     - Yes
     - No
   * - Monitor own frames
     - Yes
     - No
     - Yes
     - Yes
   * - Unproto with vias
     - Yes
     - Yes
     - Yes
     - No
   * - Non-standard connections
     - Yes
     - No
     - Yes
     - No
   * - Incoming connections
     - Yes
     - No
     - Yes
     - Yes

.. rubric:: Notes

.. [#] Direwolf hard-codes all values for port capabilities, so the values
       retrieved via AGWPE will likely not match any settings specified in the
       Direwolf config file.
.. [#] ldsped versions prior to 1.19 do not include the time data structures,
       only the string representation.


Additional notes
----------------

- ldsped allows a port on the host to be configured as read-only. When using
  a port configured in this way, functions such as monitoring will behave
  normally, while others such as attempting to register a callsign will
  silently fail.
- PyHam PE requires version 0.0.0.73 or higher of QtSoundModem due to some
  issues with QTSM's AGWPE protocol implementation in earlier versions.
