# Beka

[![Build Status](https://travis-ci.org/samrussell/beka.svg?branch=master)](https://travis-ci.org/samrussell/beka)
[![Maintainability](https://api.codeclimate.com/v1/badges/8e36eef2ae39e0ef60ae/maintainability)](https://codeclimate.com/github/samrussell/beka/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/8e36eef2ae39e0ef60ae/test_coverage)](https://codeclimate.com/github/samrussell/beka/test_coverage)

Beka is a fairly basic BGP speaker. It can send
and receive unicast route updates in IPv4 and IPv6,
but not too much else. It is designed to be simple to use
and to extend, without too much overhead.

It uses eventlet for concurrency, but is easy enough to port to
gevent if that takes your fancy.

More information at https://github.com/samrussell/beka
