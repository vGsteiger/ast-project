import re
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import argparse
from operator import attrgetter
import os
import statistics

# Constants
TEMP_FILE = "data.csv"

# Regex patterns
start_of_iteration_pattern = re.compile(r"Starting framework with the following arguments: Namespace\(verbose=False, output='/Users/viktorgsteiger/Documents/ast-project/testing_output(\d+)', show=False, timeout=(\d+), timeout_creduce=(\d+), timeout_creduce_iteration=(\d+), max_iterations=50, random=True, example=None, csmith='csmith', csmith_include='/opt/homebrew/Cellar/csmith/2.3.0/include/csmith-2.3.0', csmith_max_expr_complexity=(\d+), csmith_max_block_depth=(\d+), csmith_stop_by_stmt=(\d+), csmith_seed=0, creduce='creduce', candidates=20, compiler='(clang|g\+\+-13)', compiler_flag='(O0|O1|O2|O3)', regenerate=False\)")
iteration_pattern = re.compile(r"Iteration (\d+)")
best_candidate_pattern = re.compile(r"Best candidate this iteration: (.+)")
interesting_pattern = re.compile(r"Best candidate info: \((\d+), (\d+)\)")
best_heuristic_value = re.compile(r"Best heuristic value this iteration: (\d+\.\d+)")

# Generic method to plot using one y-axis and save result as png
def plot_one_y_axis(csv_data_str, plot_path, x_label, y_label):
    with open(TEMP_FILE, 'w') as results_file:
        results_file.write("col1,col2\n")
        results_file.write(csv_data_str)
    tips = pd.read_csv(TEMP_FILE)
    sns.set_theme(style="white", palette="deep")
    res_plt = sns.pointplot(data=tips, x="col1", y="col2")
    res_plt.set(xlabel=x_label, ylabel=y_label)
    plt.tight_layout()
    plt.savefig(plot_path)
    plt.clf()
    os.remove(TEMP_FILE)

# Same as above, but with 2 y-axes
def plot_two_y_axes(csv_data_str, plot_path, x_label, y_label, y2_label):
    with open(TEMP_FILE, 'w') as results_file:
        results_file.write("col1,col2,col3\n")
        results_file.write(csv_data_str)
    tips = pd.read_csv(TEMP_FILE)
    sns.set_theme(style="white", palette="deep")
    res_plt = sns.pointplot(data=tips, x="col1", y="col2")
    res_plt.set(xlabel=x_label, ylabel=y_label)
    ax2 = plt.twinx()
    res_plt = sns.pointplot(data=tips, x="col1", y="col3", color='r', ax=ax2)
    res_plt.set(ylabel=y2_label)
    plt.tight_layout()
    plt.savefig(plot_path)
    plt.clf()
    os.remove(TEMP_FILE)

# Wrapper class to represent a test run
class TestRun:
    def __init__(self, run_params_list):
        self.id_no = run_params_list[0]
        self.timeout = run_params_list[1]
        self.timeout_creduce = run_params_list[2]
        self.timeout_creduce_iteration = run_params_list[3]
        self.csmith_max_expr_complexity = run_params_list[4]
        self.csmith_max_block_depth = run_params_list[5]
        self.csmith_stop_by_stmt = run_params_list[6]
        self.compiler = run_params_list[7]
        self.compiler_flag = run_params_list[8]
        self.run_log = run_params_list[9]
        self.best_heuristic = max([float(val) for val in best_heuristic_value.findall(self.run_log)])
        self.best_code_size = min([float(val[0]) for val in interesting_pattern.findall(self.run_log)])  # TODO: Fix to use real best
        self.best_binary_size = max([float(val[1]) for val in interesting_pattern.findall(self.run_log)])  # TODO: Fix to use real best
    
    # Plot the source and binary size of this specific run over the iterations
    def plot_code_size_binary_size(self, plot_path):
        # Variables to store information
        iteration = None
        best_candidate = None
        source_size = None
        binary_size = None
        csv_data_string = ""

        for line in self.run_log.splitlines():
            #print(line)
            # Check if this line has information on a new iteration
            match_iteration = iteration_pattern.search(line)
            if match_iteration:
                # Save the iteration number
                iteration = match_iteration.group(1)
                # Reset the other variables
                best_candidate = None
                source_size = None
                binary_size = None
            
            # Check if this line has information on the best candidate this iteration
            match_best_candidate = best_candidate_pattern.search(line)
            if match_best_candidate:
                # Save the path to the best candidate
                best_candidate = match_best_candidate.group(1)
            
            # Check if this line has interesting information on source and binary size
            match_interesting = interesting_pattern.search(line)
            if match_interesting:
                # Save the source size and binary size
                source_size = match_interesting.group(1)
                binary_size = match_interesting.group(2)
            
            # Check if this iteration has ended
            if best_candidate and source_size and binary_size:
                # Transform the source size and binary size to kB
                source_size = int(source_size) / 1000
                binary_size = int(binary_size) / 1000
                csv_data_string += f"{iteration},{source_size},{binary_size}\n"
                # Reset the variables
                best_candidate = None
                source_size = None
                binary_size = None

        # Plot using generic function
        plot_two_y_axes(csv_data_string, plot_path, "Iterations", "Code Size [kB]", "Binary Size [kB]")


    # Plot the heuristic value of this specific run over the iterations
    def plot_heuristic(self, plot_path):
        # Variables to store information
        iteration = None
        best_candidate = None
        heuristic_val = None
        csv_data_string = ""

        for line in self.run_log.splitlines():
            #print(line)
            # Check if this line has information on a new iteration
            match_iteration = iteration_pattern.search(line)
            if match_iteration:
                # Save the iteration number
                iteration = match_iteration.group(1)
                # Reset the other variables
                best_candidate = None
                heuristic_val = None
            
            # Check if this line has information on the best candidate this iteration
            match_best_candidate = best_candidate_pattern.search(line)
            if match_best_candidate:
                # Save the path to the best candidate
                best_candidate = match_best_candidate.group(1)
            
            # Check if this line has interesting information on source and binary size
            match_heuristic = best_heuristic_value.search(line)
            if match_heuristic:
                # Save the source size and binary size
                heuristic_val = match_heuristic.group(1)
            
            # Check if this iteration has ended
            if best_candidate and heuristic_val:
                csv_data_string += f"{iteration},{heuristic_val}\n"
                # Reset the variables
                best_candidate = None
                heuristic_val = None

        # Plot using generic function
        plot_one_y_axis(csv_data_string, plot_path, "Iterations", "Heuristic Value")

def create_plots(log_file, plot_folder):
    # Read log file
    srcreduce_log = open(log_file, "r").read()

    # Create plot output folder
    if not os.path.exists(plot_folder):
        os.makedirs(plot_folder)

    # Creating TestRun objects
    runs_metadata = start_of_iteration_pattern.split(srcreduce_log)[1:]
    test_run_objects = []
    for i in range(len(runs_metadata) // 10):
        test_run_objects.append(TestRun(runs_metadata[i*10:((i+1)*10)]))

    # Plotting best example
    best_run = max(test_run_objects, key=attrgetter('best_heuristic'))
    best_run.plot_code_size_binary_size(os.path.join(plot_folder, "best_run_sizes.png"))
    best_run.plot_heuristic(os.path.join(plot_folder, "best_run_heuristic.png"))

    ###########################################
    # Plotting complexity vs. size difference #
    ###########################################

    # Classify runs in three groups
    low_complexity_runs = [run for run in test_run_objects if run.csmith_max_expr_complexity == '5']
    medium_complexity_runs = [run for run in test_run_objects if run.csmith_max_expr_complexity == '10']
    high_complexity_runs = [run for run in test_run_objects if run.csmith_max_expr_complexity == '15']
    print("Plotting complexity vs size difference, here are the datapoint counts:")
    print("Low", len(low_complexity_runs))
    print("Medium", len(medium_complexity_runs))
    print("High", len(high_complexity_runs))
    print()

    # Plot average complexity
    low_complexity_source_avg = statistics.mean([float(run.best_code_size) for run in low_complexity_runs])
    low_complexity_binary_avg = statistics.mean([float(run.best_binary_size) for run in low_complexity_runs])
    low_complexity_heuristic_avg = statistics.mean([float(run.best_heuristic) for run in low_complexity_runs])
    medium_complexity_source_avg = statistics.mean([float(run.best_code_size) for run in medium_complexity_runs])
    medium_complexity_binary_avg = statistics.mean([float(run.best_binary_size) for run in medium_complexity_runs])
    medium_complexity_heuristic_avg = statistics.mean([float(run.best_heuristic) for run in medium_complexity_runs])
    high_complexity_source_avg = statistics.mean([float(run.best_code_size) for run in high_complexity_runs])
    high_complexity_binary_avg = statistics.mean([float(run.best_binary_size) for run in high_complexity_runs])
    high_complexity_heuristic_avg = statistics.mean([float(run.best_heuristic) for run in high_complexity_runs])

    csv_data_string = f"Low,{low_complexity_source_avg},{low_complexity_binary_avg}\n"
    csv_data_string += f"Medium,{medium_complexity_source_avg},{medium_complexity_binary_avg}\n"
    csv_data_string += f"High,{high_complexity_source_avg},{high_complexity_binary_avg}\n"
    plot_two_y_axes(csv_data_string, os.path.join(plot_folder, "complexity_diff_sizes_avg.png"), "Complexity", "Average Code Size [kB]", "Average Binary Size [kB]")
    
    csv_data_string = f"Low,{low_complexity_heuristic_avg}\n"
    csv_data_string += f"Medium,{medium_complexity_heuristic_avg}\n"
    csv_data_string += f"High,{high_complexity_heuristic_avg}\n"
    plot_one_y_axis(csv_data_string, os.path.join(plot_folder, "complexity_diff_heuristic_avg.png"), "Complexity", "Average Heuristic Value")

    # Plot Max Complexity
    low_complexity_source_min = min([float(run.best_code_size) for run in low_complexity_runs])
    low_complexity_binary_max = max([float(run.best_binary_size) for run in low_complexity_runs])
    low_complexity_heuristic_max = max([float(run.best_heuristic) for run in low_complexity_runs])
    medium_complexity_source_min = min([float(run.best_code_size) for run in medium_complexity_runs])
    medium_complexity_binary_max = max([float(run.best_binary_size) for run in medium_complexity_runs])
    medium_complexity_heuristic_max = max([float(run.best_heuristic) for run in medium_complexity_runs])
    high_complexity_source_min = min([float(run.best_code_size) for run in high_complexity_runs])
    high_complexity_binary_max = max([float(run.best_binary_size) for run in high_complexity_runs])
    high_complexity_heuristic_max = max([float(run.best_heuristic) for run in high_complexity_runs])

    csv_data_string = f"Low,{low_complexity_source_min},{low_complexity_binary_max}\n"
    csv_data_string += f"Medium,{medium_complexity_source_min},{medium_complexity_binary_max}\n"
    csv_data_string += f"High,{high_complexity_source_min},{high_complexity_binary_max}\n"
    plot_two_y_axes(csv_data_string, os.path.join(plot_folder, "complexity_diff_sizes_max.png"), "Complexity", "Minimum Code Size [kB]", "Maximum Binary Size [kB]")
    
    csv_data_string = f"Low,{low_complexity_heuristic_max}\n"
    csv_data_string += f"Medium,{medium_complexity_heuristic_max}\n"
    csv_data_string += f"High,{high_complexity_heuristic_max}\n"
    plot_one_y_axis(csv_data_string, os.path.join(plot_folder, "complexity_diff_heuristic_max.png"), "Complexity", "Maximum Heuristic Value")
 
    ########################################
    # Plotting timeout vs. size difference #
    ########################################

    # Classify runs in two groups
    low_timeout_runs = [run for run in test_run_objects if run.timeout == '150']
    high_timeout_runs = [run for run in test_run_objects if run.timeout == '200']
    print("Plotting timeout vs size difference, here are the datapoint counts:")
    print("Low", len(low_timeout_runs))
    print("High", len(high_timeout_runs))
    print()

    # Plot average sizes
    low_timeout_source_avg = statistics.mean([float(run.best_code_size) for run in low_timeout_runs])
    low_timeout_binary_avg = statistics.mean([float(run.best_binary_size) for run in low_timeout_runs])
    low_timeout_heuristic_avg = statistics.mean([float(run.best_heuristic) for run in low_timeout_runs])
    high_timeout_source_avg = statistics.mean([float(run.best_code_size) for run in high_timeout_runs])
    high_timeout_binary_avg = statistics.mean([float(run.best_binary_size) for run in high_timeout_runs])
    high_timeout_heuristic_avg = statistics.mean([float(run.best_heuristic) for run in high_timeout_runs])

    csv_data_string = f"Low,{low_timeout_source_avg},{low_timeout_binary_avg}\n"
    csv_data_string += f"High,{high_timeout_source_avg},{high_timeout_binary_avg}\n"
    plot_two_y_axes(csv_data_string, os.path.join(plot_folder, "timeout_diff_sizes_avg.png"), "Timeout", "Average Code Size [kB]", "Average Binary Size [kB]")
    
    csv_data_string = f"Low,{low_timeout_heuristic_avg}\n"
    csv_data_string += f"High,{high_timeout_heuristic_avg}\n"
    plot_one_y_axis(csv_data_string, os.path.join(plot_folder, "timeout_diff_heuristic_avg.png"), "Timeout", "Average Heuristic Value")

    # Plot max sizes
    low_timeout_source_min = min([float(run.best_code_size) for run in low_timeout_runs])
    low_timeout_binary_max = max([float(run.best_binary_size) for run in low_timeout_runs])
    low_timeout_heuristic_max = max([float(run.best_heuristic) for run in low_timeout_runs])
    high_timeout_source_min = min([float(run.best_code_size) for run in high_timeout_runs])
    high_timeout_binary_max = max([float(run.best_binary_size) for run in high_timeout_runs])
    high_timeout_heuristic_max = max([float(run.best_heuristic) for run in high_timeout_runs])

    csv_data_string = f"Low,{low_timeout_source_min},{low_timeout_binary_max}\n"
    csv_data_string += f"High,{high_timeout_source_min},{high_timeout_binary_max}\n"
    plot_two_y_axes(csv_data_string, os.path.join(plot_folder, "timeout_diff_sizes_max.png"), "Timeout", "Minimum Code Size [kB]", "Maximum Binary Size [kB]")
    
    csv_data_string = f"Low,{low_timeout_heuristic_max}\n"
    csv_data_string += f"High,{high_timeout_heuristic_max}\n"
    plot_one_y_axis(csv_data_string, os.path.join(plot_folder, "timeout_diff_heuristic_max.png"), "Timeout", "Maximum Heuristic Value")

    #######################################################
    # Plotting compiler optimizations vs. size difference #
    #######################################################

    # Classify runs in four groups
    no_opt_runs = [run for run in test_run_objects if run.compiler_flag == 'O0']
    low_opt_runs = [run for run in test_run_objects if run.compiler_flag == 'O1']
    medium_opt_runs = [run for run in test_run_objects if run.compiler_flag == 'O2']
    high_opt_runs = [run for run in test_run_objects if run.compiler_flag == 'O3']
    print("Plotting compiler optimization vs size difference, here are the datapoint counts:")
    print("O0", len(no_opt_runs))
    print("O1", len(low_opt_runs))
    print("O2", len(medium_opt_runs))
    print("O3", len(high_opt_runs))
    print()

    # Plot average sizes
    no_opt_source_avg = statistics.mean([float(run.best_code_size) for run in no_opt_runs])
    no_opt_binary_avg = statistics.mean([float(run.best_binary_size) for run in no_opt_runs])
    no_opt_heuristic_avg = statistics.mean([float(run.best_heuristic) for run in no_opt_runs])
    low_opt_source_avg = statistics.mean([float(run.best_code_size) for run in low_opt_runs])
    low_opt_binary_avg = statistics.mean([float(run.best_binary_size) for run in low_opt_runs])
    low_opt_heuristic_avg = statistics.mean([float(run.best_heuristic) for run in low_opt_runs])
    medium_opt_source_avg = statistics.mean([float(run.best_code_size) for run in medium_opt_runs])
    medium_opt_binary_avg = statistics.mean([float(run.best_binary_size) for run in medium_opt_runs])
    medium_opt_heuristic_avg = statistics.mean([float(run.best_heuristic) for run in medium_opt_runs])
    high_opt_source_avg = statistics.mean([float(run.best_code_size) for run in high_opt_runs])
    high_opt_binary_avg = statistics.mean([float(run.best_binary_size) for run in high_opt_runs])
    high_opt_heuristic_avg = statistics.mean([float(run.best_heuristic) for run in high_opt_runs])

    csv_data_string = f"O0,{no_opt_source_avg},{no_opt_binary_avg}\n"
    csv_data_string += f"O1,{low_opt_source_avg},{low_opt_binary_avg}\n"
    csv_data_string += f"O2,{medium_opt_source_avg},{medium_opt_binary_avg}\n"
    csv_data_string += f"O3,{high_opt_source_avg},{high_opt_binary_avg}\n"
    plot_two_y_axes(csv_data_string, os.path.join(plot_folder, "opt_diff_sizes_avg.png"), "Optimization flag", "Average Code Size [kB]", "Average Binary Size [kB]")

    csv_data_string = f"O0,{no_opt_heuristic_avg}\n"
    csv_data_string += f"O1,{low_opt_heuristic_avg}\n"
    csv_data_string += f"O2,{medium_opt_heuristic_avg}\n"
    csv_data_string += f"O3,{high_opt_heuristic_avg}\n"
    plot_one_y_axis(csv_data_string, os.path.join(plot_folder, "opt_diff_heuristic_avg.png"), "Optimizaton flag", "Average Heuristic Value")

    # Plot max sizes
    no_opt_source_min = min([float(run.best_code_size) for run in no_opt_runs])
    no_opt_binary_max = max([float(run.best_binary_size) for run in no_opt_runs])
    no_opt_heuristic_max = max([float(run.best_heuristic) for run in no_opt_runs])
    low_opt_source_min = min([float(run.best_code_size) for run in low_opt_runs])
    low_opt_binary_max = max([float(run.best_binary_size) for run in low_opt_runs])
    low_opt_heuristic_max = max([float(run.best_heuristic) for run in low_opt_runs])
    medium_opt_source_min = min([float(run.best_code_size) for run in medium_opt_runs])
    medium_opt_binary_max = max([float(run.best_binary_size) for run in medium_opt_runs])
    medium_opt_heuristic_max = max([float(run.best_heuristic) for run in medium_opt_runs])
    high_opt_source_min = min([float(run.best_code_size) for run in high_opt_runs])
    high_opt_binary_max = max([float(run.best_binary_size) for run in high_opt_runs])
    high_opt_heuristic_max = max([float(run.best_heuristic) for run in high_opt_runs])

    csv_data_string = f"O0,{no_opt_source_min},{no_opt_binary_max}\n"
    csv_data_string += f"O1,{low_opt_source_min},{low_opt_binary_max}\n"
    csv_data_string += f"O2,{medium_opt_source_min},{medium_opt_binary_max}\n"
    csv_data_string += f"O3,{high_opt_source_min},{high_opt_binary_max}\n"
    plot_two_y_axes(csv_data_string, os.path.join(plot_folder, "opt_diff_sizes_max.png"), "Optimization flag", "Minimum Code Size [kB]", "Maximum Binary Size [kB]")

    csv_data_string = f"O0,{no_opt_heuristic_max}\n"
    csv_data_string += f"O1,{low_opt_heuristic_max}\n"
    csv_data_string += f"O2,{medium_opt_heuristic_max}\n"
    csv_data_string += f"O3,{high_opt_heuristic_max}\n"
    plot_one_y_axis(csv_data_string, os.path.join(plot_folder, "opt_diff_heuristic_max.png"), "Optimization flag", "Maximum Heuristic Value")


#######################################################################################
# Sample usage: python extract_and_plot.py srcreduce_cleaned.log.keep srcreduce_plots #
#######################################################################################
if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("log_file", help="Path to the (cleaned) log file")
    argparser.add_argument("plot_folder", help="Path to the output plot folder")
    args = argparser.parse_args()
    create_plots(args.log_file, args.plot_folder)
