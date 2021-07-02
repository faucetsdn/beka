#!/usr/bin/env python3

"""Beka setup script"""

import sys

from setuptools import setup

if sys.version_info < (3,):
    print("""You are trying to install beka on python {py}

beka is not compatible with python 2, please upgrade to python 3.5 or newer."""
          .format(py='.'.join([str(v) for v in sys.version_info[:3]])), file=sys.stderr)
    sys.exit(1)

setup(
    name='beka',
    setup_requires=['pbr>=1.9', 'setuptools>=17.1'],
    python_requires='>=3.5',
    pbr=True
)
