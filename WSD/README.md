The project tests how different context sizes affect disambiguation quality and sentiment score.

Next steps:
- create a test harness to test improvements
- run with different contexts and models (larger)
- measure accuracy
- visualize the results in tables or charts ?
- try to fix the MWE problem

### In github there are a lot of materials, so here you can read the guide.
## Explanation:
MWE FINAL - the folder with the results of MWE experiment. There are 2 folders: LIST and 1-3 DEFINITIONS, which means files with the results of 2 experiments.

NEW 100 sent 3-3 - results of WSD, where the structure is "sentences before - target word - sentences after".

NEW 100 sent 3-0 - results of WSD, where the structure is "sentences before - target word".

FINAL_report.pdf - pdf file with the final report.

LATEX report - the file with report's code from Latex.

* All result files contain: total accuracy and other metrics for every model, statistics and tagged files.

#### How to run the code:
Before running the code with certain model, you should install this version of model in the server.

