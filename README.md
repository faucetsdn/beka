# Beka

[![Build Status](https://travis-ci.com/faucetsdn/beka.svg?branch=master)](https://travis-ci.com/faucetsdn/beka)
[![Maintainability](https://api.codeclimate.com/v1/badges/a97c1287222d20baa4eb/maintainability)](https://codeclimate.com/github/faucetsdn/beka/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/a97c1287222d20baa4eb/test_coverage)](https://codeclimate.com/github/faucetsdn/beka/test_coverage)

Beka is a fairly basic BGP speaker. It can send
and receive unicast route updates in IPv4 and IPv6,
but not too much else. It is designed to be simple to use
and to extend, without too much overhead.

It uses eventlet for concurrency, but is easy enough to port to
gevent if that takes your fancy.

More information at https://github.com/faucetsdn/beka
