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


def generate_source_code(args):
    if args.example is not None:
        logging.info("Generating source code based on example file: %s", args.example)
        with open(args.example, "r") as f:
            source_code = f.read()
    elif args.random:
        source_code = ""
        # Generate random source code with csmith:
        cmsmith_args = (
            "--max-expr-complexity="
            + str(args.size)
            + " --max-expr-depth="
            + str(args.size)
        )
        if args.optional_csmith_args is not None:
            cmsmith_args += " " + args.optional_csmith_args
        source_code = subprocess.check_output(
            [args.csmith, cmsmith_args], universal_newlines=True
        ).decode("utf-8")
    else:
        logging.error("No source code generation method specified")
        sys.exit(1)
    # Show source code
    if args.show:
        print(source_code)

    return source_code


def run_framework(args, source_code):
    start_time: int = time.time()

    last_source_code: str = source_code
    last_binary_path: str = None
    last_heuristic_value: float = None
    i = 0

    while start_time + args.timeout > time.time() and i < args.max_iterations:
        candidates: list[str] = generate_reduced_source_code_candidates(
            args, source_code
        )
        candidates: list[str] = filter_reduced_source_code_candidates(
            args, source_code, candidates
        )

        candidate_scores: dict[str:float] = dict()

        for candidate in candidates:
            binary_path: str = compile_source_code(args, candidate)
            if binary_path is None:
                logging.error("Compilation failed")
                continue

            heuristic_value: float = calculate_heuristic_value(
                args, source_code, candidate, last_binary_path, binary_path
            )
            if heuristic_value > last_heuristic_value:
                candidates.remove(candidate)
                continue

            candidate_scores[candidate] = heuristic_value

        if len(candidate_scores) == 0:
            logging.info("No further reduction possible")
            break

        best_candidate: str = min(candidate_scores, key=candidate_scores.get)
        last_source_code = best_candidate
        last_binary_path = compile_source_code(args, best_candidate)
        last_heuristic_value = candidate_scores[best_candidate]

    if args.show:
        print(last_source_code)

    with open(args.generated, "w") as f:
        f.write(last_source_code)

    if i == args.max_iterations:
        logging.info("Finished after %d iterations", i)
    else:
        logging.info("Finished after %d seconds", time.time() - start_time)


def calculate_source_code_size(source_code) -> int:
    with open("temp.c", "w") as f:
        f.write(source_code)

    size = os.path.getsize("temp.c")

    os.remove("temp.c")

    return size


def calculate_binary_size(binary_path) -> int:
    return os.path.getsize(binary_path)


def calculate_binary_size_difference(binary1_path, binary2_path) -> int:
    return math.fabs(os.path.getsize(binary1_path) - os.path.getsize(binary2_path))


def calculate_heuristic_value(
    args,
    original_source_code,
    reduced_source_code,
    original_binary_path,
    reduced_binary_path,
) -> float:
    # TODO: Implement this
    return 0


def generate_reduced_source_code_candidates(args, source_code) -> list[str]:
    num_candidates = args.cvsise_candidates

    # TODO: Are these the correct options?
    cvise_options = [
        "--reduce",
        f"--count={num_candidates}",
        "--output-directory=candidates",
        "--max-iterations=1000",
    ]

    # Use C-Vise to generate the candidates
    subprocess.run([args.cvsise, *cvise_options, source_code], check=True)

    # Read the candidates from the output directory
    candidates = []
    for file in os.listdir("candidates"):
        with open(os.path.join("candidates", file), "r") as f:
            candidates.append(f.read())

    # Remove the output directory
    shutil.rmtree("candidates")

    return candidates


def filter_reduced_source_code_candidates(args, source_code, candidates) -> list[str]:
    for candidate in candidates:
        if calculate_source_code_size(candidate) >= calculate_source_code_size(
            source_code
        ):
            candidates.remove(candidate)
    return candidates


def compile_source_code(args, source_code) -> str:
    source_file_binary = get_random_file_name()
    source_file_name = source_file_binary + ".c"

    # Create a temporary file for the source code
    with open(source_file_name, "w") as f:
        f.write(source_code)

    # Use gcc to compile the source code
    try:
        subprocess.check_output(
            [args.compiler, source_file_name, "-o", source_file_binary, args.compiler_args],
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        # Compilation failed, print the error message and return None
        print("Compilation failed with error:\n", e.output.decode())
        return None
    finally:
        # Remove the temporary source code file
        os.remove(source_file_name)

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
    parser.add_argument("--cvise", type=str, help="path to cvise", required=True)
    parser.add_argument(
        "--cvsise-canidates", type=int, help="number of cvsise canidates", default=20
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

    # Check if framework exists
    if not os.path.exists(args.framework):
        logging.error("Framework does not exist: %s", args.framework)
        sys.exit(1)

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
    run_framework(args, source_code)


if __name__ == "__main__":
    main()
