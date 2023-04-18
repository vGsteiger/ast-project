# Finding Small Code with Large Binaries

Project repository for Automatic Software Testing lecture

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

## Usage

### Source code reduction

The source code reduction is implemented in the `srcreduce` module. It can be used as follows:

```bash
$ python3 -m srcreduce -h
usage: srcreduce [-h] [-v] [-o OUTPUT] [-s] [-t TIMEOUT] [-m MAX_ITERATIONS]
                 [-i INITIAL_SIZE] [-r] [-e EXAMPLE]
```

The following options are available:

- `-h`, `--help`: Show help message and exit
- `-v`, `--verbose`: Show verbose output
- `-o OUTPUT`, `--output OUTPUT`: Output file for the generated source code
- `-s`, `--show`: Show the generated source code
- `-t TIMEOUT`, `--timeout TIMEOUT`: Timeout for the framework in seconds
- `-m MAX_ITERATIONS`, `--max-iterations MAX_ITERATIONS`: Maximum number of iterations
- `-i INITIAL_SIZE`, `--initial-size INITIAL_SIZE`: Initial size of the source code
- `-r`, `--random`: Use random source code generation
- `-e EXAMPLE`, `--example EXAMPLE`: Use example source code generation based on the given example file
- `--optional-csmith-args OPTIONAL_CSMITH_ARGS`: Optional arguments for csmith
- `--csmith`: Path to csmith binary
- `--cvise`: Path to cvise binary
- `--cvsise-canidates`: Number of cvise candidates, default: 20
- `--compiler`: Path to compiler binary
- `--compiler-args`: Optional arguments for compiler
