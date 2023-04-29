import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt

for i in range(1,6):

    tips = pd.read_csv("plotdata" + str(i) + ".data")

    sns.set_theme(style="white", palette="deep")
    res_plt = sns.pointplot(data=tips, x="iter", y="code_size")
    res_plt.set(xlabel='Iterations', ylabel='Code Size [kB]', title=('Exemplary reduction ' + str(i)))
    ax2 = plt.twinx()
    res_plt = sns.pointplot(data=tips, x="iter", y="bin_size", color='r', ax=ax2)
    res_plt.set(ylabel='Binary Size [kB]')
    plt.tight_layout()
    plt.savefig("plot" + str(i) + ".png")
    plt.clf()
