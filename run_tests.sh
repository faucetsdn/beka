#!/bin/bash
FILE_NAME=$(readlink -f "$0")
set -e  # quit on error

BEKA_ROOT=$(dirname "$FILE_NAME")

PIP_INSTALL=0
UNIT_TEST=0
CODE_CHECK=0

# allow user to skip parts of test
while getopts "nuz" o "${BEKA_TESTS}"; do
  case "${o}" in
        n)
            CODE_CHECK=1
            ;;
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

# ============================= Code Checks =============================
if [ "$CODE_CHECK" == 1 ] ; then
    if [ "$PIP_INSTALL" == 1 ] ; then
        echo "=============== Installing Pypi Dependencies ================="
        pip3 install --upgrade --cache-dir=/var/tmp/pip-cache \
            -r "${BEKA_ROOT}/codecheck-requirements.txt"
    fi

    echo "=============== Running PyType ===================="
    time PYTHONPATH="${BEKA_ROOT}" pytype --config "${BEKA_ROOT}/setup.cfg" \
        "${BEKA_ROOT}/beka/"

    echo "=============== Running Pylint ===================="
    time "${BEKA_ROOT}/test/codecheck/pylint.sh"
fi
