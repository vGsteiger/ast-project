import re
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import argparse


def plot(log_file, plot_file):
    # Regex patterns
    iteration_pattern = re.compile(r"Iteration (\d+)")
    best_candidate_pattern = re.compile(r"Best candidate this iteration: (.+)")
    interesting_pattern = re.compile(r"Best candidate info: \((\d+), (\d+)\)")

    # Variables to store information
    iteration = None
    best_candidate = None
    source_size = None
    binary_size = None

    # Write information to csv file
    with open('results.csv', 'w') as results_file:

        # Write header
        results_file.write('iter,source_size,binary_size\n')

        with open(log_file, "r") as f:
            for line in f:
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
                    results_file.write(f"{iteration},{source_size},{binary_size}\n")
                    # Reset the variables
                    best_candidate = None
                    source_size = None
                    binary_size = None

    tips = pd.read_csv('results.csv')

    sns.set_theme(style="white", palette="deep")
    res_plt = sns.pointplot(data=tips, x="iter", y="source_size")
    res_plt.set(xlabel='Iterations', ylabel='Code Size [kB]')
    ax2 = plt.twinx()
    res_plt = sns.pointplot(data=tips, x="iter", y="binary_size", color='r', ax=ax2)
    res_plt.set(ylabel='Binary Size [kB]')
    plt.tight_layout()
    plt.savefig(plot_file)
    plt.clf()

if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("log_file", help="Path to the log file")
    argparser.add_argument("plot_file", help="Path to the plot file")
    args = argparser.parse_args()
    plot(args.log_file, args.plot_file)