# marshmallow-jit

[![Tests](https://github.com/mesemus/torched-marshmallow/actions/workflows/test.yml/badge.svg)](https://github.com/mesemus/torched-marshmallow/actions/workflows/test.yml)
[![CI - Full Matrix](https://github.com/mesemus/torched-marshmallow/actions/workflows/ci.yml/badge.svg)](https://github.com/mesemus/torched-marshmallow/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/mesemus/torched-marshmallow/branch/main/graph/badge.svg)](https://codecov.io/gh/mesemus/torched-marshmallow)
[![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![Marshmallow](https://img.shields.io/badge/marshmallow-3%20%7C%204-green.svg)](https://marshmallow.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Code base

This library uses code and concepts from the DeepFriedMarhsmallow library.
The reason why the library is not used as it is is that we need to support more advanced scenarios to which this library is not designed for,
such as schemas where error propagatin is important and should be optimized as well. This is not feasible in the current implementation of DeepFriedMarshmallow.
