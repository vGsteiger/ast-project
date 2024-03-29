# Finding Small Code with Large Binaries

Project repository for Automatic Software Testing lecture project

## Students

- Viktor Gsteiger (<vgsteiger@student.ethz.ch>)
- Nikodem Kernbach (<nkernbach@student.ethz.ch>)

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

```bash
# Add csmith include to cpath
export CPATH="[path to include dir of csmith installation]"
```

Additionally, we suggest to use a virtual environment for the project. You can create a virtual environment with the following command:

```bash
python3 -m venv scrReduceEnv
```

You can activate the virtual environment with the following command:

```bash
source scrReduceEnv/bin/activate
```

### Source code reduction

The source code reduction is implemented in the `srcreduce` module. You can install the module with the following command:

```bash
pip install -e .
```

It can be used as follows:

```bash
$ srcReduce -h
usage: srcReduce [-h] [-v] [-o OUTPUT] [-t TIMEOUT] [--timeout-creduce TIMEOUT_CREDUCE] [--timeout-creduce-iteration TIMEOUT_CREDUCE_ITERATION]
                 [-m MAX_ITERATIONS] [-r] [-e EXAMPLE] --csmith CSMITH --csmith-include CSMITH_INCLUDE
                 [--csmith-max-expr-complexity CSMITH_MAX_EXPR_COMPLEXITY] [--csmith-max-block-depth CSMITH_MAX_BLOCK_DEPTH]
                 [--csmith-stop-by-stmt CSMITH_STOP_BY_STMT] [--csmith-seed CSMITH_SEED] --creduce CREDUCE [--candidates CANDIDATES] --compiler COMPILER
                 [--compiler-flag COMPILER_FLAG] [--regenerate] [--batch-measurements BATCH_MEASUREMENTS] [--batch-output-csv BATCH_OUTPUT_CSV]
```

The following options are available:

```bash
  -h, --help                                                show this help message and exit
  -v, --verbose                                             show verbose output
  -o OUTPUT, --output OUTPUT                                output directory
  -t TIMEOUT, --timeout TIMEOUT                             timeout for the framework in seconds
  --timeout-creduce TIMEOUT_CREDUCE                         timeout for creduce passes in seconds
  --timeout-creduce-iteration TIMEOUT_CREDUCE_ITERATION     timeout for creduce per iteration in seconds
  -m MAX_ITERATIONS, --max-iterations MAX_ITERATIONS        maximum number of iterations
  -r, --random                                              use random source code generation
  -e EXAMPLE, --example EXAMPLE                             use example source code generation based on the given example file
  --csmith CSMITH                                           path to csmith
  --csmith-include CSMITH_INCLUDE                           path to csmith include
  --csmith-max-expr-complexity CSMITH_MAX_EXPR_COMPLEXITY   maximum expression complexity
  --csmith-max-block-depth CSMITH_MAX_BLOCK_DEPTH           maximum block depth
  --csmith-stop-by-stmt CSMITH_STOP_BY_STMT                 stop generating code after this many statements
  --csmith-seed CSMITH_SEED                                 seed for csmith
  --creduce CREDUCE                                         path to creduce
  --candidates CANDIDATES                                   number of cvsise canidates
  --compiler COMPILER                                       path to compiler
  --compiler-flag COMPILER_FLAG                             compiler flag
  --regenerate                                              generate new code if no new candidates are found for the current initial code
  --batch-measurements BATCH_MEASUREMENTS                   special modes used to collect a lot of measurements in order to create plots
  --batch-output-csv BATCH_OUTPUT_CSV                       used together with batch measurement mode, specifies path to output csv file
```

### Example

The following command can be used to reduce the size of a random generated source code:

```bash
srcReduce  --csmith csmith --creduce creduce --compiler gcc --random --output [OUTPUT_DIR] --csmith-include [CSMITH_UNCLUDE] --timeout-creduce 10 --timeout-creduce-iteration 150 --timeout 900
```
