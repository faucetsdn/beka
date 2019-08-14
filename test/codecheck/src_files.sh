#!/bin/bash

BEKAHOME=`dirname $0`"/../.."
for i in beka test ; do find $BEKAHOME/$i/ -type f -name '[a-z]*.py' ; done
