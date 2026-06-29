# Lexical Conceptual Mapping and Metaphor Tracking

This project implements a unified data pipeline developed for the Advanced Computational Linguistics (LCM-2026) course at Palacký University Olomouc. The framework maps surface lexical units to abstract conceptual schemas by tracing hypernym lineage chains in WordNet.

## Project Structure

* `metaphor_full_pipeline_final.py` - The main unified Python script containing all 4 operational modes.
* `chainnet_metonymy.json` - Configuration file containing structural relations for Mode 1.
* `thesaurus.json` - Master lexicographical database containing 8,747 entries used for Mode 3.
* `metaphor_report.tex` - The complete LaTeX source code for the 6–10 page final report.
* `metaphor_report.tex` - The complete LaTeX source code for the 6–10 page final report.
* `final_report_latex.txt` - The complete code in LaTeX fo my report.
* `README.md` - This file (project documentation and execution guide).

## Requirements

Before running the pipeline, ensure you have the `wn` library installed:

```bash
pip install wn

python metaphor_full_pipeline_final.py --mode chainnet

python metaphor_full_pipeline_final.py --mode wordnet

python metaphor_full_pipeline_final.py --mode thesaurus

python metaphor_full_pipeline_final.py --mode discovery
