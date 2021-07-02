# Beka

[![Build Status](https://github.com/faucetsdn/beka/workflows/Unit%20tests/badge.svg?branch=master)](https://github.com/faucetsdn/beka/actions?query=workflow%3A%22Unit+tests%22)
[![Test Coverage](https://codecov.io/gh/faucetsdn/beka/branch/master/graph/badge.svg)](https://codecov.io/gh/faucetsdn/beka)

Beka is a fairly basic BGP speaker. It can send
and receive unicast route updates in IPv4 and IPv6,
but not too much else. It is designed to be simple to use
and to extend, without too much overhead.

It uses eventlet for concurrency, but is easy enough to port to
gevent if that takes your fancy.

More information at https://github.com/faucetsdn/beka
