from setuptools import setup

long_description = """
    Beka is a fairly basic BGP speaker. It can send
    and receive unicast route updates in IPv4 and IPv6,
    but not too much else. It is designed to be simple to use
    and to extend, without too much overhead.

    It uses eventlet for concurrency, but is easy enough to port to
    gevent if that takes your fancy.

    More information at https://github.com/samrussell/beka
"""

setup(
    name='beka',
    description='A bare-bones BGP speaker',
    long_description=long_description,
    version='0.3.3',
    url='https://github.com/samrussell/beka',
    author='Sam Russell',
    author_email='sam.h.russell@gmail.com',
    license='Apache2',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3'
    ],
    keywords='bgp beka routing sdn networking',
    packages=['beka'],
    python_requires='>=3',
    install_requires=[
        'eventlet'
    ]
)
