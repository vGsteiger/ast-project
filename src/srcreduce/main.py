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
from statistics import mean, quantiles


logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="srcreduce.log",
    filemode='a'
)

class PercentileList:
    def __init__(self):
        self.percentile_list = []

    def add_item(self, item):
        self.percentile_list.append(item)
        self.percentile_list.sort()

    def get_mean(self):
        return mean(self.percentile_list)
    
    # Return 1st and 99th percentile
    def get_percentile(self):
        quant = quantiles(self.percentile_list, n=100)
        return (quant[1], quant[98])
    
    # Checks whether 99th percentiles are within 5% of the mean
    def check_percentile(self):
        current_mean = self.get_mean()
        lower_bound = current_mean - 0.05*current_mean
        upper_bound = current_mean + 0.05*current_mean
        lower_quant, upper_quant = self.get_percentile()
        return lower_bound <= lower_quant and upper_quant <= upper_bound


def generate_source_code(args):
    if args.example is not None:
        logging.info("Generating source code based on example file: %s", args.example)
        with open(args.example, "r") as f:
            source_code = f.read()
    elif args.random:
        logging.info("Generating random source code")
        source_code = ""
        # Generate random source code with csmith:
        cmsmith_args = "--max-expr-complexity=" + str(args.csmith_max_expr_complexity)
        cmsmith_args += " --max-block-depth=" + str(args.csmith_max_block_depth)
        cmsmith_args += " --stop-by-stmt=" + str(args.csmith_stop_by_stmt)
        cmsmith_args += " --seed=" + str(args.csmith_seed)
        source_code = subprocess.check_output([args.csmith], universal_newlines=True)
        src_code_diopter_obj = SourceProgram(code=source_code, language=Language.C)
        sanitizer = Sanitizer()
        # Note: csmith include path must be in CPATH
        if not sanitizer.check_for_compiler_warnings(src_code_diopter_obj) and not sanitizer.check_for_ub_and_address_sanitizer_errors(src_code_diopter_obj):
            logging.error("Generated source code contains compiler warnings or UB")
            return generate_source_code(args)
    else:
        logging.error("No source code generation method specified")
        sys.exit(1)

    return source_code

def gen_and_save_src_code(args, init_iter):
    source_code = generate_source_code(args)

    src_code_path = args.output + "/init" + str(init_iter) + ".c"
    
    logging.info("Writing source code to file: %s", src_code_path)
    # Write source code to file
    with open(src_code_path, "w") as f:
        f.write(source_code)

    return src_code_path

def new_run(args, opt_category_param='', save_iters=False):
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
    next_code_init = args.output + "/init0.c"

    first_candidate = gen_and_save_src_code(args, init_iter)
    candidates_pq.append((0, first_candidate))

    if save_iters:
        size, bin_size = calculate_source_and_binary_size(args, next_code_init)
        with open(args.batch_output_csv, "a+") as f:
            f.write(f"Source,{size},0\n")
            f.write(f"Binary,{bin_size},0\n") 
    
    logging.info("Reducing")
    start_time = time.time()

    while start_time + args.timeout > time.time() and iter < args.max_iterations:
        iter += 1
        if len(candidates_pq) == 0 and args.regenerate:
            logging.info("No candidates left, generating new source code")
            init_iter += 1
            next_code_init = gen_and_save_src_code(args, init_iter)
            next_code_path = next_code_init
        else:
            candidates_pq.sort(reverse=True)
            next_code_path = candidates_pq.pop(0)[1]
        
        logging.info("Init code iter %d", init_iter)
        logging.info("Iteration %d", iter)

        candidates_dir: str = generate_reduced_source_code_candidate(args, next_code_path, iter)

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
                next_code_path,
                candidate,
            )

            candidates_pq.append((heuristic_value, candidate))

        candidates_pq.sort(reverse=True)
        if len(candidates_pq) == 0:
            logging.info("No new candidates this iteration")
            if save_iters:
                with open(args.batch_output_csv, "a+") as f:
                    f.write(f"Source,{size},{iter}\n")
                    f.write(f"Binary,{bin_size},{iter}\n") 
        else:
            best_candidate_this_iter = candidates_pq[0][1]
            best_heuristic_this_iter = candidates_pq[0][0]
            size, bin_size = calculate_source_and_binary_size(args, best_candidate_this_iter)
            logging.info("Best candidate this iteration: %s", best_candidate_this_iter)
            logging.info("Best heuristic value this iteration: %f", best_heuristic_this_iter)
            logging.info("Best candidate info: %s", (size, bin_size))
            if save_iters:
                with open(args.batch_output_csv, "a+") as f:
                    f.write(f"Source,{size},{iter}\n")
                    f.write(f"Binary,{bin_size},{iter}\n") 
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

    # Used to print info in the end and retrieve info in batch mode
    info_dict = {}
    if args.batch_measurements is not None and not save_iters:
        calculate_heuristic_value(args, best_code_init, best_code_path, retrieve_info=info_dict)
        with open(args.batch_output_csv, "a+") as f:
            f.write(f"Source,{info_dict['src']},{opt_category_param}\n")
            f.write(f"Binary,{info_dict['bin']},{opt_category_param}\n")
    else:
        calculate_heuristic_value(args, best_code_init, best_code_path)

    if iter == args.max_iterations:
        logging.info("Finished after %d iterations", iter)
    else:
        logging.info("Finished after %d seconds", time.time() - start_time)

    if args.batch_measurements is not None and not save_iters:
        return info_dict['src'], info_dict['bin']


def calculate_source_and_binary_size(args, source_code_path):
    if source_code_path is None:
        logging.error("No source code path given")
        return 0, 0
    size = os.path.getsize(source_code_path)

    devnull = open(os.devnull, "w")

    subprocess.run(
        [
            args.compiler,
            f"{source_code_path}",
            "-o",
            "temp.o",
            "-" + args.compiler_flag,
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
    retrieve_info=None
) -> float:
    # Size of the .text-section from the binary sample (larger is better).
    # (2) Size of the corresponding code sample (must not be larger than the original, smaller is better).
    # (3) Binary size to source code ratio (larger is better).

    logging.info("Calculating heuristic value for %s and comparing to %s", reduced_source_code_path, original_source_code_path)

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
    
    if reduced_source_code_size <= 500:
        # Special case for file that is always 500 bytes because only contains a single function declaration
        return 0

    logging.info(f"Comparing original source code {original_source_code_path} with {reduced_source_code_path}")
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

    if retrieve_info is not None:
        retrieve_info['src'] = reduced_source_code_size
        retrieve_info['bin'] = reduced_bin_size

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

    interestingness_test = f"""
#!/bin/bash
{args.compiler} {source_code_path} -o orig.o -{args.compiler_flag} -w -I{args.csmith_include}
{args.compiler} {local_new_source_code_path} -o tmp.o -{args.compiler_flag} -w -I{args.csmith_include}
./tmp.o

# If the new binary does not run at all, it is not interesting
if [ $? -ne 0 ]; then
    exit 1
fi

# If the new soure code is smaller than 500 bytes, it is not interesting
if [ $(wc -c < {local_new_source_code_path}) -lt 500 ]; then
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

def cleanup_or_create_output_folder(args) -> None:
    # Cleanup output dir
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    else:
        # Remove everything in the output directory
        shutil.rmtree(args.output)
        os.makedirs(args.output)


def main():
    # Create argument parser
    parser = argparse.ArgumentParser(description="Source code reducer")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="show verbose output"
    )
    parser.add_argument("-o", "--output", type=str, help="output directory")
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
    parser.add_argument("--csmith", type=str, help="path to csmith", required=True)
    parser.add_argument(
        "--csmith-include", type=str, help="path to csmith include", required=True
    )
    parser.add_argument("--csmith-max-expr-complexity", type=int, default=10, help="maximum expression complexity")
    parser.add_argument("--csmith-max-block-depth", type=int, default=5, help="maximum block depth")
    parser.add_argument("--csmith-stop-by-stmt", type=int, default=100, help="stop generating code after this many statements")
    parser.add_argument("--csmith-seed", type=int, default=0, help="seed for csmith")
    parser.add_argument("--creduce", type=str, help="path to creduce", required=True)
    parser.add_argument(
        "--candidates", type=int, help="number of cvsise canidates", default=20
    )
    parser.add_argument("--compiler", type=str, help="path to compiler", required=True)
    parser.add_argument("--compiler-flag", type=str, help="compiler flag", default="")
    parser.add_argument("--regenerate", action="store_true", help="generate new code if no new candidates are found for the current initial code", default=False)

    parser.add_argument("--batch-measurements", type=str, help="Special mode used by developers to collect a lot of measurements used to create plots", default=None)
    parser.add_argument("--batch-output-csv", type=str, help="Used together with batch measurement mode, specifies path to output csv file", default='data.csv')

    # Parse arguments
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        format="%(levelname)s: %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )
    logging.info("Starting framework with the following arguments: %s", args)

    # Check if source code example file
    if args.example is not None and not os.path.exists(args.example):
        logging.error("Example file does not exist: %s", args.example)
        sys.exit(1)

    cleanup_or_create_output_folder(args)

    # Run framework normally
    if args.batch_measurements is None:
        logging.info("Running framework normally")
        try:
            new_run(args)
        finally:
            logging.info("Done")
            for item in os.listdir(os.getcwd()):
                if item.endswith(".orig") or item.endswith(".c"):
                    os.remove(item)
    # Run framework in batch measurement mode
    elif args.batch_measurements == 'complexity':
        i = 0
        output_folder_base = args.output
        complexity_params = {'Low': (5, 2, 50), 'Medium': (10, 5, 100), 'High': (15, 8, 150)}
        with open(args.batch_output_csv, "w") as f:
            f.write("type,size,category\n")
        for (complexity, level) in complexity_params.items():
            (args.csmith_max_expr_complexity, args.csmith_max_block_depth, args.csmith_stop_by_stmt) = level
            logging.info("Expr compl is " + str(args.csmith_max_expr_complexity))
            bin_sizes_perc_list = PercentileList()
            src_sizes_perc_list = PercentileList()
            #while not (i >= 10 and src_sizes_perc_list.check_percentile() and bin_sizes_perc_list.check_percentile()):
            for _ in range(10):
                i += 1
                args.output = output_folder_base + str(i)
                cleanup_or_create_output_folder(args)
                try:
                    src_size, bin_size = new_run(args, opt_category_param=complexity)
                    src_sizes_perc_list.add_item(src_size)
                    bin_sizes_perc_list.add_item(bin_size)
                finally:
                    logging.info("Done")
                    for item in os.listdir(os.getcwd()):
                        if item.endswith(".orig") or item.endswith(".c"):
                            os.remove(item)
                    continue
    elif args.batch_measurements == 'optimizations':
        i = 0
        output_folder_base = args.output
        optimization_params = ['O0', 'O1', 'O2', 'O3']
        with open(args.batch_output_csv, "w") as f:
            f.write("type,size,category\n")
        for level in optimization_params:
            args.compiler_flag = level
            logging.info("Compiler flag is " + str(args.compiler_flag))
            bin_sizes_perc_list = PercentileList()
            src_sizes_perc_list = PercentileList()
            #while not (i >= 10 and src_sizes_perc_list.check_percentile() and bin_sizes_perc_list.check_percentile()):
            for _ in range(10):
                i += 1
                args.output = output_folder_base + str(i)
                cleanup_or_create_output_folder(args)
                try:
                    src_size, bin_size = new_run(args, opt_category_param=level)
                    src_sizes_perc_list.add_item(src_size)
                    bin_sizes_perc_list.add_item(bin_size)
                finally:
                    logging.info("Done")
                    for item in os.listdir(os.getcwd()):
                        if item.endswith(".orig") or item.endswith(".c"):
                            os.remove(item)
                    continue
    elif args.batch_measurements == 'timeout':
        i = 0
        output_folder_base = args.output
        timeout_params = {'5': (5, 25), '10': (10, 50), '15': (15, 75), '20': (20, 100), '25': (25, 125)}
        with open(args.batch_output_csv, "w") as f:
            f.write("type,size,category\n")
        for (timeout_str, timeouts) in timeout_params.items():
            (args.timeout_creduce, args.timeout_creduce_iteration) = timeouts
            logging.info("Creduce timeout is " + str(args.timeout_creduce))
            bin_sizes_perc_list = PercentileList()
            src_sizes_perc_list = PercentileList()
            #while not (i >= 10 and src_sizes_perc_list.check_percentile() and bin_sizes_perc_list.check_percentile()):
            for _ in range(10):
                i += 1
                args.output = output_folder_base + str(i)
                cleanup_or_create_output_folder(args)
                try:
                    src_size, bin_size = new_run(args, opt_category_param=timeout_str)
                    src_sizes_perc_list.add_item(src_size)
                    bin_sizes_perc_list.add_item(bin_size)
                finally:
                    logging.info("Done")
                    for item in os.listdir(os.getcwd()):
                        if item.endswith(".orig") or item.endswith(".c"):
                            os.remove(item)
                    continue
    elif args.batch_measurements == 'single':
        i = 0 
        output_folder_base = args.output
        with open(args.batch_output_csv, "w") as f:
            f.write("type,size,category\n")
        for _ in range(2):
            i += 1
            args.output = output_folder_base + str(i)
            cleanup_or_create_output_folder(args)
            try:
                new_run(args, save_iters=True)
            finally:
                logging.info("Done")
                for item in os.listdir(os.getcwd()):
                    if item.endswith(".orig") or item.endswith(".c"):
                        os.remove(item)
                continue



if __name__ == "__main__":
    main()
