import sys
import os
import argparse
import logging
import subprocess
import time
import random
import string
import math
import shutil
import stat


def generate_source_code(args):
    if args.example is not None:
        logging.info("Generating source code based on example file: %s", args.example)
        with open(args.example, "r") as f:
            source_code = f.read()
    elif args.random:
        logging.info("Generating random source code")
        source_code = ""
        # Generate random source code with csmith:
        cmsmith_args = (
            "--max-expr-complexity="
            + str(len(vars(args)))
        )
        if args.optional_csmith_args is not None:
            cmsmith_args += " " + args.optional_csmith_args
        source_code = subprocess.check_output(
            [args.csmith], universal_newlines=True
        )
    else:
        logging.error("No source code generation method specified")
        sys.exit(1)
    # Show source code
    if args.show:
        print(source_code)

    return source_code


def run(args):
    start_time: int = time.time()

    last_source_code_path: str = os.path.abspath(args.output)
    last_binary_path: str = None
    last_heuristic_value: float = None
    i = 0

    logging.info("Reducing")

    while start_time + args.timeout > time.time() and i < args.max_iterations:
        logging.info("Iteration %d", i)
        for i in range(5):
            candidate: str = generate_reduced_source_code_candidate(
                args, last_source_code_path, i
            )

            if candidate is None:
                logging.error("Candidate generation failed")
                continue

            logging.info(candidate)

            candidate_scores: dict[str:float] = dict()

            binary_path: str = compile_source_code(args, candidate)
            if binary_path is None:
                logging.error("Compilation failed")
                continue

            heuristic_value: float = calculate_heuristic_value(
                args, last_source_code_path, candidate, last_binary_path, binary_path
            )

            candidate_scores[candidate] = heuristic_value

        best_candidate: str = min(candidate_scores, key=candidate_scores.get)
        logging.info("Best candidate: %s", best_candidate)
        logging.info("Heuristic value: %f", candidate_scores[best_candidate])
        if last_heuristic_value is not None and candidate_scores[best_candidate] >= last_heuristic_value:
            logging.info("No improvement")
        else:
            logging.info("Improvement")
            last_source_code_path = best_candidate
            last_binary_path = compile_source_code(args, best_candidate)
            last_heuristic_value = candidate_scores[best_candidate]

    shutil.copyfile(last_source_code_path, args.generated)

    if i == args.max_iterations:
        logging.info("Finished after %d iterations", i)
    else:
        logging.info("Finished after %d seconds", time.time() - start_time)


def calculate_source_code_size(source_code_path) -> int:
    return os.path.getsize(source_code_path)

def calculate_source_and_binary_size(args, source_code_path):
    size = os.path.getsize(source_code_path)

    res = subprocess.run(["gcc", f"{source_code_path}", "-o", "temp.o", "-w", f"-I{args.csmith_include}"], check=True)

    bin_size = os.path.getsize("temp.o")

    print(size, " test ", bin_size)

    os.remove("temp.o")

    return size, bin_size


def calculate_binary_size(binary_path) -> int:
    return os.path.getsize(binary_path)


def calculate_binary_size_difference(binary1_path, binary2_path) -> int:
    return math.fabs(os.path.getsize(binary1_path) - os.path.getsize(binary2_path))


def calculate_heuristic_value(
    args,
    original_source_code_path,
    reduced_source_code_path,
    original_binary_path,
    reduced_binary_path,
) -> float:
    # TODO: Implement this
    return 0


def generate_reduced_source_code_candidate(args, source_code_path, iteration) -> str:
    num_candidates = args.candidates

    if args.cvise:
        return generate_cvise_candidates(args, source_code_path, num_candidates)
    elif args.creduce:
        return generate_creduce_candidate(args, source_code_path, num_candidates, iteration)
    else:
        logging.error("No valid candidate generation method specified")
        sys.exit(1)


def generate_creduce_candidate(args, source_code_path, num_candidates, iteration) -> str:
    credue_options = [
    ]

    if source_code_path.split("_")[-1].split(".")[0].isdigit():
        new_source_code_path = source_code_path.split("_")[:-2] + f"_{iteration}.c"
    else:
        new_source_code_path = source_code_path[:-2] + f"_{iteration}.c"

    shutil.copyfile(source_code_path, new_source_code_path)

    local_new_source_code_path = os.path.basename(new_source_code_path)

    # TODO: Make this faster, improve as it is part of the heuristic
    interestingness_test = f"""
    #!/bin/bash
    gcc {source_code_path} -o orig.o -w -I{args.csmith_include}
    gcc {local_new_source_code_path} -o tmp.o -w -I{args.csmith_include}

    # If the new binary does not run at all, it is not interesting
    if [ $? -ne 0 ]; then
        exit 1
    fi

    # If the new binary is bigger than the original, it is interesting
    if [ $(stat -f%z tmp.o) -ge $(($(stat -f%z orig.o) - 1)) ]; then
        exit 0
    fi

    exit 1
    """

    with open("interestingness_test.sh", "w") as f:
        f.write(interestingness_test)
    
    os.chmod("interestingness_test.sh", 0o777)

    logging.info("Running creduce")

    subprocess.run(
        [
            args.creduce,
            "interestingness_test.sh",
            new_source_code_path,
            *credue_options,
        ]
    )
    
    return new_source_code_path

# TODO: source_code is now a path, not a file!
def generate_cvise_candidates(args, source_code, num_candidates) -> list[str]:

    sz, bin_sz = calculate_source_and_binary_size(args, source_code)
    with open("temp.c", "w") as f:
        f.write(source_code)

# IS THIS THE HEURISTIC???
# problem: cvise needs to pass the test on the input c file -> the binary size does not go up, rather stays the same
# -> sol1?: try to save more than one candidates and filter according to own heuristic
# (-> sol2?: try to use different check (ratio instead of size)) -> does not help much
# -> sol3?: try to provide cvise with regressional value instead of boolean (possible?)
    testing_script_py = """
import sys
import subprocess
import os
subprocess.run(["gcc", "temp.c", "-o", "temp.o", "-w", "-I/home/nikch/csmith-install/include/"], check=True)    
bin_size = os.path.getsize("temp.o")
if bin_size >= """ + str(bin_sz) + """:
  print("0")
  sys.exit(0)
else:
  print("1")
  sys.exit(1)
    """

    with open("testing_script_py.py", "w") as f:
        f.write(testing_script_py)
    testing_script = """
cp /home/nikch/Documents/Repositories/ast-project/testing_script_py.py .
python testing_script_py.py
    """
    with open("testing_script.sh", "w") as f:
        f.write(testing_script)
    st = os.stat('testing_script.sh')
    os.chmod('testing_script.sh', st.st_mode | stat.S_IEXEC)

    # Use C-Vise to generate the candidates
#    subprocess.run([args.cvise, *cvise_options, source_code], check=True)
    #SUUUUPER slow...
    subprocess.run([args.cvise, "testing_script.sh", "temp.c", "--timeout", "1"], check=True)

    # Read the candidates from the output directory
#    candidates = []
#    for file in os.listdir("candidates"):
#        with open(os.path.join("candidates", file), "r") as f:
#            candidates.append(f.read())

    # Remove the output directory
#    shutil.rmtree("candidates")

    with open("temp.c", "r") as f:
        candidate = f.read()

    return [candidate] #candidates

def compile_source_code(args, source_code_path) -> str:
    source_file_binary = get_random_file_name()

    # Use gcc to compile the source code
    try:
        subprocess.run(
            [args.compiler, source_code_path, "-o", source_file_binary, args.compiler_args, "-E -P"],
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        # Compilation failed, print the error message and return None
        print("Compilation failed with error:\n", e.output.decode())
        return None

    # Compilation succeeded, return the path to the binary
    binary_path = os.path.abspath(source_file_binary)
    return binary_path


def get_random_file_name() -> str:
    return "".join(
        random.choice(string.ascii_lowercase + string.digits) for _ in range(10)
    )


def main():
    # Create argument parser
    parser = argparse.ArgumentParser(description="Source code reducer")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="show verbose output"
    )
    parser.add_argument(
        "-o", "--output", type=str, help="initial generated source code file"
    )
    parser.add_argument("-g", "--generated", type=str, help="reduced source code file")
    parser.add_argument(
        "-s", "--show", action="store_true", help="show the generated source code"
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=10,
        help="timeout for the framework in seconds",
    )
    parser.add_argument(
        "-m",
        "--max-iterations",
        type=int,
        default=1000,
        help="maximum number of iterations",
    )
    parser.add_argument(
        "-i",
        "--initial-size",
        type=int,
        default=100,
        help="initial size of the source code",
    )
    parser.add_argument(
        "-r", "--random", action="store_true", help="use random source code generation"
    )
    parser.add_argument(
        "-e",
        "--example",
        type=str,
        help="use example source code generation based on the given example file",
    )
    parser.add_argument(
        "--optional-csmith-args", type=str, help="optional csmith arguments"
    )
    parser.add_argument("--csmith", type=str, help="path to csmith", required=True)
    parser.add_argument("--csmith-include", type=str, help="path to csmith include", required=True)
    parser.add_argument("--cvise", type=str, help="path to cvise")
    parser.add_argument("--creduce", type=str, help="path to creduce")
    parser.add_argument(
        "--candidates", type=int, help="number of cvsise canidates", default=20
    )
    parser.add_argument("--compiler", type=str, help="path to compiler", required=True)
    parser.add_argument("--compiler-args", type=str, help="compiler arguments")

    # Parse arguments
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        format="%(levelname)s: %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    # Check if source code example file
    if args.example is not None and not os.path.exists(args.example):
        logging.error("Example file does not exist: %s", args.example)
        sys.exit(1)

    # Generate source code
    source_code = generate_source_code(args)

    # Write source code to file
    with open(args.output, "w") as f:
        f.write(source_code)

    # Run framework
    logging.info("Running framework")
    run(args)


if __name__ == "__main__":
    main()

# cmd: python src/srcreduce/main.py --csmith /home/nikch/csmith-install/bin/csmith --cvise cvise --compiler g++ --random --output tmpsrc.c --csmith-include /home/nikch/csmith-install/include/ --generated tmpsrc_reduced.c
# achtung, hardgecodete paths etc...
# es macht schonmal, aber dauert etwas zu lange zurzeit

# cmd: python src/srcreduce/main.py --csmith csmith --creduce creduce --compiler g++ --random --output tmpsrc.c --generated tmpsrc_reduced.c --csmith-include /opt/homebrew/Cellar/csmith/2.3.0/include/