#!/bin/sh

yapf --recursive --in-place .
flake8 .
