import sys
import os
import argparse
import logging
import subprocess
import time
import random
import string
import shutil


def generate_source_code(args):
    if args.example is not None:
        logging.info("Generating source code based on example file: %s", args.example)
        with open(args.example, "r") as f:
            source_code = f.read()
    elif args.random:
        logging.info("Generating random source code")
        source_code = ""
        # Generate random source code with csmith:
        cmsmith_args = "--max-expr-complexity=" + str(len(vars(args)))
        if args.optional_csmith_args is not None:
            cmsmith_args += " " + args.optional_csmith_args
        source_code = subprocess.check_output([args.csmith], universal_newlines=True)
    else:
        logging.error("No source code generation method specified")
        sys.exit(1)

    return source_code


def run(args, initial_output):
    start_time: int = time.time()

    last_source_code_path: str = initial_output
    last_heuristic_value: float = None
    i = 0

    logging.info("Reducing")

    while start_time + args.timeout > time.time() and i < args.max_iterations:
        logging.info("Iteration %d", i)
        candidates_dir: str = generate_reduced_source_code_candidate(
            args, last_source_code_path, i
        )

        if candidates_dir is None:
            logging.error("Candidate generation failed")
            continue

        candidates_scores: dict[str:float] = dict()

        logging.info("Compiling candidates")

        for candidate in os.listdir(candidates_dir):
            if not candidate.endswith(".c"):
                continue

            candidate = os.path.join(candidates_dir, candidate)

            binary_path: str = compile_source_code(args, candidate)
            if binary_path is None:
                logging.error("Compilation failed")
                continue

            heuristic_value: float = calculate_heuristic_value(
                args,
                last_source_code_path,
                candidate,
            )

            candidates_scores[candidate] = heuristic_value

        best_candidate: str = max(candidates_scores, key=candidates_scores.get)
        logging.info("Best candidate this iteration: %s", best_candidate)
        logging.info("Best heuristic value this iteration: %f", candidates_scores[best_candidate])
        # TODO: Local minimum detection -> start over with some previous version
        # TODO: If this is still not improving, start over with a random new code
        if last_heuristic_value is not None:
            logging.info("Best heuristic value so far: %f", last_heuristic_value)
        if (
            last_heuristic_value is not None
            and candidates_scores[best_candidate] < last_heuristic_value
        ):
            logging.info("No improvement")
        else:
            logging.info("Improvement")
            last_source_code_path = best_candidate
            last_heuristic_value = candidates_scores[best_candidate]

        i += 1

    last_file_path = args.output + "/last.c"
    shutil.copyfile(last_source_code_path, last_file_path)

    if i == args.max_iterations:
        logging.info("Finished after %d iterations", i)
    else:
        logging.info("Finished after %d seconds", time.time() - start_time)


def calculate_source_and_binary_size(args, source_code_path):
    size = os.path.getsize(source_code_path)

    devnull = open(os.devnull, "w")

    subprocess.run(
        [
            args.compiler,
            f"{source_code_path}",
            "-o",
            "temp.o",
            "-w",
            f"-I{args.csmith_include}",
        ],
        stdout=devnull,
        stderr=devnull,
    )

    bin_size = calculate_size("temp.o")

    os.remove("temp.o")

    return size, bin_size


def calculate_size(path) -> int:
    # Tranform this size tmp.o | awk '{{print $1}}' | tail -n 1 into a python function
    return int(
        subprocess.check_output(
            ["size", path],
            universal_newlines=True,
        )
        .split("\n")[1]
        .split("\t")[0]
    )


def calculate_size_difference(
    args, path1, path2
) -> tuple[int, int, int, int, int, int]:
    source_code_size1, bin_size1 = calculate_source_and_binary_size(args, path1)
    source_code_size2, bin_size2 = calculate_source_and_binary_size(args, path2)
    return (
        source_code_size1 - source_code_size2,
        bin_size1 - bin_size2,
        source_code_size2,
        bin_size2,
        bin_size1,
        source_code_size1,
    )


def calculate_heuristic_value(
    args,
    original_source_code_path,
    reduced_source_code_path,
) -> float:
    # Size of the .text-section from the binary sample (larger is better).
    # (2) Size of the corresponding code sample (must not be larger than the original, smaller is better).
    # (3) Binary size to source code ratio (larger is better).

    (
        source_code_size_difference,
        bin_size_difference,
        reduced_source_code_size,
        reduced_bin_size,
        original_bin_size,
        original_source_code_size,
    ) = calculate_size_difference(
        args, original_source_code_path, reduced_source_code_path
    )

    if source_code_size_difference < 0:
        return 0

    if bin_size_difference > 0:
        return 0

    logging.info(
        "Source code size difference: %d, binary size difference: %d",
        source_code_size_difference,
        bin_size_difference,
    )
    logging.info(
        "Initial source code size: %d, initial binary size: %d",
        original_source_code_size,
        original_bin_size,
    )
    logging.info(
        "Reduced source code size: %d, reduced binary size: %d",
        reduced_source_code_size,
        reduced_bin_size,
    )
    logging.info("Ratio: %f", reduced_bin_size / reduced_source_code_size)

    # TODO: Large difference to previously generated mutants where we utilize similarity measures

    return reduced_bin_size / reduced_source_code_size


def generate_reduced_source_code_candidate(args, source_code_path, iteration) -> str:
    credue_options = [
        "--save-temps",
        "--timeout",
        str(args.timeout_creduce),
    ]

    # Get current location:
    iteration_dir = args.output + f"/iteration-{iteration}"
    os.makedirs(iteration_dir, exist_ok=True)

    new_source_code_path = args.output + f"/iteration-{iteration}/init_{iteration}.c"

    shutil.copyfile(source_code_path, new_source_code_path)

    # Remove iteration-{iteration} from the path (DO NOT REMOVE THIS, OTHERWISE CREDUCE WILL NOT WORK)
    source_code_path_for_count_line_markers = new_source_code_path.split("/")[:-3] + [
        new_source_code_path.split("/")[-1]
    ]
    source_code_path_for_count_line_markers = "/".join(
        source_code_path_for_count_line_markers
    )

    shutil.copyfile(source_code_path, source_code_path_for_count_line_markers)

    local_new_source_code_path = os.path.basename(new_source_code_path)

    # TODO: Make this faster, improve as it is part of the heuristic
    interestingness_test = f"""
#!/bin/bash
{args.compiler} {source_code_path} -o orig.o -w -I{args.csmith_include}
{args.compiler} {local_new_source_code_path} -o tmp.o -w -I{args.csmith_include}
./tmp.o

# If the new binary does not run at all, it is not interesting
if [ $? -ne 0 ]; then
    exit 1
fi

# If the new binary is bigger than the original, it is interesting
if [ $(size tmp.o | awk '{{print $1}}' | tail -n 1) -ge $(size orig.o | awk '{{print $1}}' | tail -n 1) ]; then
    # Save the file for later and add random number to the end
    # Generate unique random string:
    random_string=$(mktemp XXXXXXXXXXXXXXXX)
    # Copy the file to the current location with a random name
    cp {local_new_source_code_path} {iteration_dir}/interesting_${{random_string}}.c
    exit 0
fi

exit 1
"""

    with open("interestingness_test.sh", "w") as f:
        f.write(interestingness_test)

    os.chmod("interestingness_test.sh", 0o777)

    logging.info("Running creduce")

    try:
        subprocess.run(
            [
                args.creduce,
                "interestingness_test.sh",
                new_source_code_path,
                *credue_options,
            ],
            timeout=args.timeout_creduce_iteration,
        )
    except subprocess.TimeoutExpired:
        logging.info("CReduce timed out")

    return iteration_dir


def compile_source_code(args, source_code_path) -> str:
    source_file_binary = source_code_path[:-2] + ".o"

    devnull = open(os.devnull, "w")

    # Use gcc to compile the source code
    try:
        subprocess.run(
            [
                args.compiler,
                source_code_path,
                "-o",
                source_file_binary,
                f"-I{args.csmith_include}",
            ],
            stdout=devnull,
            stderr=devnull,
        )
    except subprocess.CalledProcessError as e:
        # Compilation failed, print the error message and return None
        logging.error("Compilation failed with error:\n", e.output.decode())
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
    parser.add_argument("-o", "--output", type=str, help="output directory")
    parser.add_argument(
        "-s", "--show", action="store_true", help="show the generated source code"
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=300,
        help="timeout for the framework in seconds",
    )
    parser.add_argument(
        "--timeout-creduce",
        type=int,
        default=2,
        help="timeout for creduce passes in seconds",
    )
    parser.add_argument(
        "--timeout-creduce-iteration",
        type=int,
        default=15,
        help="timeout for creduce per iteration in seconds",
    )
    parser.add_argument(
        "-m",
        "--max-iterations",
        type=int,
        default=50,
        help="maximum number of iterations",
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
    parser.add_argument(
        "--csmith-include", type=str, help="path to csmith include", required=True
    )
    parser.add_argument("--creduce", type=str, help="path to creduce", required=True)
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

    initial_output = args.output + "/init.c"

    if not os.path.exists(args.output):
        os.makedirs(args.output)
    else:
        # Remove everything in the output directory
        shutil.rmtree(args.output)
        os.makedirs(args.output)
        
    # Write source code to file
    with open(initial_output, "w") as f:
        f.write(source_code)

    # Run framework
    logging.info("Running framework")
    try:
        run(args, initial_output)
    finally:
        logging.info("Done")
        for item in os.listdir(os.getcwd()):
            if item.endswith(".orig") or item.endswith(".c"):
                os.remove(item)


if __name__ == "__main__":
    main()

# cmd: python src/srcreduce/main.py --csmith csmith --creduce creduce --compiler gcc --random --output /Users/viktorgsteiger/Documents/ast-project/testing_output --csmith-include /opt/homebrew/Cellar/csmith/2.3.0/include/csmith-2.3.0
