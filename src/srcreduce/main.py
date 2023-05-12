import sys
import os
import argparse
import logging
import subprocess
import time
import random
import string
import shutil
sys.path.append(os.getcwd()+"/src/srcreduce/diopter")
from diopter.compiler import Language
from diopter.compiler import SourceProgram
from diopter.sanitizer import Sanitizer


logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="srcreduce.log",
    filemode='a'
)

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
        src_code_diopter_obj = SourceProgram(code=source_code, language=Language.C)
        sanitizer = Sanitizer()
        # Note: csmith include path must be in CPATH
        if not sanitizer.check_for_compiler_warnings(src_code_diopter_obj) and not sanitizer.check_for_ub_and_address_sanitizer_errors(src_code_diopter_obj):
            return generate_source_code(args)
    else:
        logging.error("No source code generation method specified")
        sys.exit(1)

    return source_code

def gen_and_save_src_code(args, init_iter):
    source_code = generate_source_code(args)

    src_code_path = args.output + "/init" + str(init_iter) + ".c"
        
    # Write source code to file
    with open(src_code_path, "w") as f:
        f.write(source_code)

    return src_code_path

def new_run(args):
    start_time: int = time.time()
    # counts iterations
    iter: int = 0
    # counts iterations of new sampled codes
    init_iter: int = 0
    
    candidates_pq = []
    best_code_path = None
    best_code_heuristic = None
    best_code_init = None
    next_code_path = None
    next_code_heuristic = None
    next_code_init = None    
    
    logging.info("Reducing")
    #max iterations = max no of creduce runs
    while start_time + args.timeout > time.time() and iter < args.max_iterations:
        iter += 1
        if len(candidates_pq) == 0:
            init_iter += 1
            next_code_init = gen_and_save_src_code(args, init_iter)
            next_code_path = next_code_init
            next_code_heuristic = calculate_heuristic_value(args, next_code_init, next_code_path)
        else:
            candidates_pq.sort(reverse=True)
            next_code_path = candidates_pq.pop(0)[1]
            next_code_heuristic = calculate_heuristic_value(args, next_code_init, next_code_path)
        
        logging.info("Init code iter %d", init_iter)
        logging.info("Iteration %d", iter)

        candidates_dir: str = generate_reduced_source_code_candidate(args, next_code_path, iter)
        #candidates_scores: dict[str:float] = dict()
#        candidates_info: dict[str: tuple[str, str]] = dict()
        logging.info("Compiling candidates")
        for candidate in os.listdir(candidates_dir):
            if not candidate.endswith(".c"):
                continue
            
            candidate = os.path.join(candidates_dir, candidate)

            # Sanitizer check
            with open(candidate, "r") as f:
                source_code = f.read()
            src_code_diopter_obj = SourceProgram(code=source_code, language=Language.C)
            sanitizer = Sanitizer()
            # Note: csmith include path must be in CPATH
            if not sanitizer.check_for_compiler_warnings(src_code_diopter_obj) and not sanitizer.check_for_ub_and_address_sanitizer_errors(src_code_diopter_obj):
                continue

            binary_path: str = compile_source_code(args, candidate)
            if binary_path is None:
                logging.error("Compilation failed")
                continue

            heuristic_value: float = calculate_heuristic_value(
                args,
                next_code_init,
                candidate,
#                candidates_info
            )

            if heuristic_value > next_code_heuristic:
                candidates_pq.append((heuristic_value, candidate))

        candidates_pq.sort(reverse=True)
        if len(candidates_pq) == 0:
            logging.info("No new candidates this iteration")
        else:
            best_candidate_this_iter = candidates_pq[0][1]
            best_heuristic_this_iter = candidates_pq[0][0]
            logging.info("Best candidate this iteration: %s", best_candidate_this_iter)
            logging.info("Best heuristic value this iteration: %f", best_heuristic_this_iter)
#            logging.info("Best candidate info: %s", candidates_info[best_heuristic_this_iter])
            if best_code_heuristic is None or best_heuristic_this_iter > best_code_heuristic:
                logging.info("This iters best is global best")
                best_code_path = best_candidate_this_iter
                best_code_heuristic = best_heuristic_this_iter
                best_code_init = next_code_init
            else:
                logging.info("No new global best found")

    best_file_dest_path = args.output + "/last.c"
    shutil.copyfile(best_code_path, best_file_dest_path)
    logging.info("The best code was %s", best_code_path)
    logging.info("with heuristic %f", best_code_heuristic)
    logging.info("derived from %s", best_code_init)
    # Used to print info in the end
    calculate_heuristic_value(args, best_code_init, best_code_path)

    if iter == args.max_iterations:
        logging.info("Finished after %d iterations", iter)
    else:
        logging.info("Finished after %d seconds", time.time() - start_time)


def run(args, initial_output):
    start_time: int = time.time()

    last_source_code_path: str = initial_output
    last_heuristic_value: float = None
    i = 0

    candidates_pq = []

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
        candidates_info: dict[str: tuple[str, str]] = dict()

        logging.info("Compiling candidates")

        for candidate in os.listdir(candidates_dir):
            if not candidate.endswith(".c"):
                continue

            candidate = os.path.join(candidates_dir, candidate)

            # Sanitizer check
            with open(candidate, "r") as f:
                source_code = f.read()
            src_code_diopter_obj = SourceProgram(code=source_code, language=Language.C)
            sanitizer = Sanitizer()
            # Note: csmith include path must be in CPATH
            if not sanitizer.check_for_compiler_warnings(src_code_diopter_obj) and not sanitizer.check_for_ub_and_address_sanitizer_errors(src_code_diopter_obj):
                continue


            binary_path: str = compile_source_code(args, candidate)
            if binary_path is None:
                logging.error("Compilation failed")
                continue

            heuristic_value: float = calculate_heuristic_value(
                args,
                last_source_code_path,
                candidate,
                candidates_info
            )

            candidates_scores[candidate] = heuristic_value
            # Prevents reduced code with same heuristic to be taken next round
            if last_heuristic_value is None or heuristic_value > last_heuristic_value:
                candidates_pq.append((heuristic_value, candidate))

        candidates_pq.sort()
        next_candidate = candidates_pq.pop(0)
        if next_candidate is None:
            # maybe start over with new code sample?
            break
        best_candidate: str = max(candidates_scores, key=candidates_scores.get)
        logging.info("Best candidate this iteration: %s", best_candidate)
        logging.info("Best heuristic value this iteration: %f", candidates_scores[best_candidate])
        logging.info("Best candidate info: %s", candidates_info[best_candidate])
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
    candidates_info=None,
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
    
    if reduced_source_code_size <= 18:
        # Special case for file that is always 18 bytes because only contains a single function declaration
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

    # skipping assignment if no condidates_info provided
    if candidates_info is not None:
        candidates_info[reduced_source_code_path] = (reduced_source_code_size, reduced_bin_size)

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

    # Cleanup output dir
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    else:
        # Remove everything in the output directory
        shutil.rmtree(args.output)
        os.makedirs(args.output)

    # Run framework
    logging.info("Running framework")
    try:
        new_run(args)
    finally:
        logging.info("Done")
        for item in os.listdir(os.getcwd()):
            if item.endswith(".orig") or item.endswith(".c"):
                os.remove(item)


if __name__ == "__main__":
    main()

# cmd: python src/srcreduce/main.py --csmith csmith --creduce creduce --compiler gcc --random --output /Users/viktorgsteiger/Documents/ast-project/testing_output --csmith-include /opt/homebrew/Cellar/csmith/2.3.0/include/csmith-2.3.0 --timeout-creduce 10 --timeout-creduce-iteration 150 --timeout 900
# cmd: python src/srcreduce/main.py --csmith /home/nikch/csmith-install/bin/csmith --creduce creduce --compiler gcc --random --output /home/nikch/Documents/Repositories/ast-project/testing_output --csmith-include /home/nikch/csmith-install/include
