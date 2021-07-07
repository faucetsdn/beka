#!/bin/bash
FILE_NAME=$(readlink -f "$0")
set -e  # quit on error

BEKA_ROOT=$(dirname "$FILE_NAME")

PIP_INSTALL=0
UNIT_TEST=0

# allow user to skip parts of test
while getopts "nuz" o "${BEKA_TESTS}"; do
  case "${o}" in
        u)
            UNIT_TEST=1
            ;;
        z)
            PIP_INSTALL=1
            ;;
        *)
            echo "Provided unsupported option. Exiting with code 1"
            exit 1
            ;;
    esac
done

# ============================= PIP Install =============================
if [ "$PIP_INSTALL" == 1 ] ; then
    echo "=============== Installing Pypi Dependencies ================="
    pip3 install --upgrade --cache-dir=/var/tmp/pip-cache \
        -r "${BEKA_ROOT}/test-requirements.txt" \
        -r "${BEKA_ROOT}/requirements.txt"
fi

# ============================= Unit Tests =============================
if [ "$UNIT_TEST" == 1 ] ; then
    echo "=============== Running Unit Tests ================="
    time env PYTHONPATH="${BEKA_ROOT}" pytest -v --cov=beka \
        "${BEKA_ROOT}"/test/unit/test_*.py
fi
