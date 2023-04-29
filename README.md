# Finding Small Code with Large Binaries

Project repository for Automatic Software Testing lecture project

## Students

- Viktor Gsteiger (vgsteiger@student.ethz.ch)
- Nikodem Kernbach (nkernbach@student.ethz.ch)

## Project description

To expand current research into compiler correctness we propose to also investigate non-equivalence relations in compilers such as binary size.
It is expected that compilers, when optimizing for binary size, should return a smaller binary after optimization.
Failures to do so may show potential unwanted behaviour in compilers and investigations into the code patterns that produce this behaviour may lead to specific conclusions with regard to concrete bugs in compilers.
Therefore we propose a framework that, given a source code, reduces the source code size while maximizing the binary size to source code ratio.
If successful, this tool might help to specifically show issues with regard to before mentioned non-equivalence relations in compilers.

## Project structure

The project is structured as follows:

- `src`: Contains the source code of the project
- `src/srcreduce`: Contains the source code of the source code reduction and binary size maximization framework
- `examples`: Contains example generated source code and the corresponding binary size reduction results
- `docs`: Contains the reports which make up the project documentation

## Usage

### Dependencies

You need to add the path to csmith header files to the `CPATH` environment variable for the sanitizing checks to work correctly. On ubuntu, you can add the following at the end of your `.bashrc` file and restart your machine:
```
# Add csmith include to cpath
export CPATH="[path to include dir of csmith installation]"
```

### Source code reduction

The source code reduction is implemented in the `srcreduce` module. It can be used as follows:

```bash
$ python3 -m srcreduce -h
usage: main.py [-h] [-v] [-o OUTPUT] [-s] [-t TIMEOUT] [--timeout-creduce TIMEOUT_CREDUCE]
               [--timeout-creduce-iteration TIMEOUT_CREDUCE_ITERATION] [-m MAX_ITERATIONS] [-r] [-e EXAMPLE]
               [--optional-csmith-args OPTIONAL_CSMITH_ARGS] --csmith CSMITH --csmith-include CSMITH_INCLUDE --creduce CREDUCE
               [--candidates CANDIDATES] --compiler COMPILER [--compiler-args COMPILER_ARGS]
```

The following options are available:
```bash
  -h, --help                        show this help message and exit
  -v, --verbose                     show verbose output
  -o OUTPUT, --output OUTPUT        output directory
  -s, --show                        show the generated source code
  -t TIMEOUT, --timeout TIMEOUT     timeout for the framework in seconds
  --timeout-creduce TIMEOUT_CREDUCE timeout for creduce passes in seconds
  --timeout-creduce-iteration TIMEOUT_CREDUCE_ITERATION timeout for creduce per iteration in seconds
  -m MAX_ITERATIONS, --max-iterations MAX_ITERATIONS maximum number of iterations
  -r, --random                      use random source code generation
  -e EXAMPLE, --example EXAMPLE     use example source code generation based on the given example file
  --optional-csmith-args OPTIONAL_CSMITH_ARGS optional csmith arguments
  --csmith CSMITH                   path to csmith
  --csmith-include CSMITH_INCLUDE   path to csmith include
  --creduce CREDUCE                 path to creduce
  --candidates CANDIDATES           number of cvsise canidates
  --compiler COMPILER               path to compiler
  --compiler-args COMPILER_ARGS     compiler arguments
```
