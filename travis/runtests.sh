#!/bin/bash
set -e  # quit on error

# See https://docs.travis-ci.com/user/environment-variables/#convenience-variables
echo TRAVIS_BRANCH: $TRAVIS_BRANCH
echo TRAVIS_COMMIT: $TRAVIS_COMMIT

if [ "$TRAVIS_SHARD" == "unittest" ]; then
  env BEKA_TESTS="-z" ./run_tests.sh

  env BEKA_TESTS="-u" ./run_tests.sh

  if [ "$CODE_COV" == "true" ]; then
    codecov || true
  fi

  if [ "$CODE_CHECK" == "true" ]; then
    env BEKA_TESTS="-n" ./run_tests.sh
  fi

  exit 0
fi
