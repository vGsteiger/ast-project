#!/bin/bash

# Set environment variables and source virtualenv
export CPATH="/opt/homebrew/Cellar/csmith/2.3.0/include/csmith-2.3.0"
source /Users/viktorgsteiger/.virtualenvs/ast-project/bin/activate

# Install Python package
pip install -e .

# Set up parameters
compilers=("clang" "g++-13")
timeouts_creduce=(5 10 15)
timeouts_creduce_iteration=(25 50 75)
timeouts_overall=(150 200 250)
compiler_flags=("O0" "O1" "O2" "O3")
csmith_expr_compls=(5 10 15)
csmith_max_depths=(2 5 8)
csmith_stop_by=(50 100 150)

iteration=0

# Loop through all combinations
for compiler in "${compilers[@]}"; do
  for timeout_creduce in "${timeouts_creduce[@]}"; do
    for timeout_creduce_iteration in "${timeouts_creduce_iteration[@]}"; do
      for timeout_overall in "${timeouts_overall[@]}"; do
        for compiler_flag in "${compiler_flags[@]}"; do
          for csmith_expr_compl in "${csmith_expr_compls[@]}"; do
            for csmith_max_depth in "${csmith_max_depths[@]}"; do
              for csmith_stop in "${csmith_stop_by[@]}"; do
                let iteration+=1

                # Call srcReduce with current parameter combination
                srcReduce --csmith csmith --creduce creduce --compiler "$compiler" --random --output "/Users/viktorgsteiger/Documents/ast-project/testing_output$iteration" --csmith-include "$CPATH" --timeout-creduce "$timeout_creduce" --timeout-creduce-iteration "$timeout_creduce_iteration" --timeout "$timeout_overall" --compiler-flag "$compiler_flag" --csmith-max-expr-complexity "$csmith_expr_compl" --csmith-max-block-depth "$csmith_max_depth" --csmith-stop-by-stmt "$csmith_stop"

              done
            done
          done
        done
      done
    done
  done
done
