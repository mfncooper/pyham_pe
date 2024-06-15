# PyHam PE

## Overview

This package provides a client implementation of the AGWPE protocol, enabling
and simplifying the creation of applications using that protocol in order to
communicate with servers such as Direwolf or ldsped.

A lower level API provides access to the protocol at a level close to that of
individual AGWPE frames (not to be confused with AX.25 frames), enabling the
ultimate level of control over communication with the server.

A higher level API provides abstractions helpful in building more complex
applications, transparently taking care of some of the details, such as
connection management and monitoring.

The AGWPE protocol, and thus this package, has the advantage, over other
commonly used protocols such as KISS, that it can be easily used to create
connected-mode sessions. As such, it can be used to create many types of
ham radio software, from simple beaconing to full-fledged packet radio
terminal applications akin to Linpac. (See PyHam's
[Paracon](https://paracon.readthedocs.io/)
software for an example of the latter.)

It is expected that developers working with this package will have some level
of understanding of the AGWPE protocol, though detailed knowledge is *not*
required due to the abstractions provided. Those interested in the details
may wish to refer to the
[AGWPE protocol reference](https://www.on7lds.net/42/sites/default/files/AGWPEAPI.HTM)
in conjunction with the documentation for this package.

**Author**: Martin F N Cooper, KD6YAM  
**License**: MIT License

### A note on naming

The protocol on which this package is based is commonly referred to as
AGWPE, and more properly as the AGWPE TCP/IP API. The 'AGWPE' stands
for AGW Packet Engine, where the 'AGW' comes from the callsign of the
original creator of the protocol, George Rossopoulos, SV2AGW. In order to
avoid confusion with software written by SV2AGW and using the name AGWPE,
this PyHam package uses the name PE when referring to the package, and
AGWPE when referring to the protocol.

## Installation

**Important**: This package requires Python 3.7 or later.

The PyHam PE package is distributed on
[PyPI](https://pypi.org/project/pyham_pe/),
and should be installed with pip as follows:

```console
$ pip install pyham_pe
```

Then the modules you require may be imported with the appropriate subset of the
following:

```python
   import pe
   import pe.app
   import pe.connect
   import pe.handler
   import pe.monitor
```

The source code is available from the
[GitHub repository](https://github.com/mfncooper/pyham_pe):

```console
$ git clone https://github.com/mfncooper/pyham_pe
```

## Documentation

Full documentation is available
[online](https://pyham-pe.readthedocs.io/en/latest/)
and includes the following:

<dl>
<dt><b>User Guide</b></dt>
<dd>The User Guide introduces some conceptual material and then explains the
   lower level API and gradually progresses to the simpler, higher level.</dd>
<dt><b>Compatibility</b></dt>
<dd>Some information on the level of support for the protocol that can be
   expected from the most popular AGWPE servers.</dd>
<dt><b>API Reference</b></dt>
<dd>If you are looking for information on a specific function, class, or
   method, this part of the documentation is for you.</dd>
</dl>

## Discussion

If you have questions about how to use this package, the documentation should
be your first point of reference. If the User Guide, API Reference, or
Compatibility guide don't answer your questions, or you'd simply like to share
your experiences or generally discuss this package, please join the community
on the
[PyHam PE Discussions](https://github.com/mfncooper/pyham_pe/discussions)
forum.

Note that the GitHub Issues tracker should be used only for reporting bugs or
filing feature requests, and should not be used for questions or general
discussion.

## References

<dl>
<dt>AGWPE protocol reference:</dt>
<dd><a href="https://www.on7lds.net/42/sites/default/files/AGWPEAPI.HTM">https://www.on7lds.net/42/sites/default/files/AGWPEAPI.HTM</a></dd>
</dl>

## About PyHam

PyHam is a collection of Python packages targeted at ham radio enthusiasts who
are also software developers. The name was born out of a need to find unique
names for these packages when the most obvious names were already taken.

PyHam packages aim to provide the kind of functionality that makes it much
simpler to build sophisticated ham radio applications without having to start
from scratch. In addition to the packages, PyHam aims to provide useful
real-world ham radio applications for all hams.

See the [PyHam home page](https://pyham.org) for more information, and a
list of currently available libraries and applications.
