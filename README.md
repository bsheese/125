# CS/DS 125: Introduction to Computer and Data Science

Course materials for CS/DS 125 at Illinois Wesleyan University, taught by Brad Sheese. The course teaches Python from the beginning (data types, loops, conditionals, functions, strings and lists) and then moves into pandas Series, DataFrames and plotting. It assumes no programming experience. The readings come from the course textbook, [snakebear.science](https://snakebear.science), and the folder numbers below follow its chapter numbers.

## Modules

| Folder | Textbook chapter | Topics |
|---|---|---|
| [01_intro](01_intro/) | 1 | Notebooks, running cells, a first program |
| [02_data_types_operators](02_data_types_operators/) | 2 | Data types, type errors, arithmetic operators, modulus and floor division |
| [03_loops_conditionals](03_loops_conditionals/) | 3 | For loops, conditionals, while loops, Booleans and loop control, simple programs |
| [04_functions](04_functions/) | 4 | Calling functions, importing modules, defining functions, a small betting game |
| [05_strings_lists](05_strings_lists/) | 5.1, 5.2 | String methods, lists, working with several lists at once, reading a data file |
| [06_series](06_series/) | 6 | pandas Series: labels and lookups, whole-column work, descriptive statistics, text, grouping, with optional older exercises numbered 06.9.x |
| [07_dataframes](07_dataframes/) | 7, 10 | DataFrames: first look, selecting rows, spotting problems, groups and crosstabs, with optional older exercises numbered 07.9.x |
| [08_data_vis](08_data_vis/) | 8, 9 | Choosing and reading charts: categories, one numeric column, comparing groups, two numeric columns, change over time, and fixing misleading charts |
| [data](data/) | | Datasets for module 08, with their origins |
| [pair_activities](pair_activities/) | | Notebooks for the in-class pair activities in modules 06 to 08 |

Most notebooks are exercises: the student makes a copy in Drive, fills in the code cells and submits a short response form at the end. A few are reading-response discussion notebooks (`*_Reading_Discussion`) or in-class tutorials. Optional challenge notebooks have `Challenge` in the name.

## Where the notebooks come from

Students currently open these notebooks from Colab links on Canvas, and those links point at the copies in Brad's Google Drive, not at this repository. The notebooks here were downloaded from those Drive files on 2026-10-31. [`notebook_sources.csv`](notebook_sources.csv) records, for each notebook, the Canvas item that links to it and the Drive file ID it came from. Until the Canvas links are switched to point here, an edit made in this repository does not reach students unless it is also copied back to the Drive file.

Saved outputs were cleared on import, the same convention as the 225 repository, so students run each cell themselves.

## How the notebooks get their tools and data

The "Getting started" cell at the top of each exercise clones [bsheese/cs125_tools](https://github.com/bsheese/cs125_tools), which provides the response form (`exercise_report_response`). The form posts to a Google Form only when the student ticks the "Ready" box and runs the submit cell. Datasets are downloaded from [bsheese/CSDS125ExampleData](https://github.com/bsheese/CSDS125ExampleData).

## Running locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python smoke_test.py            # run every notebook and report anything unexpected
python smoke_test.py 04 05_2    # only notebooks whose path contains a pattern
```

Because exercise cells are left blank for students, running a notebook top to bottom always produces some errors. `smoke_test.py` separates the errors an unfinished exercise produces (NameError, SyntaxError, `input()` with no keyboard) from everything else, and only the second group counts as a failure. Cells that raise an error on purpose carry the Jupyter tag `raises-exception`, and a cell that must not run unattended (a deliberate infinite loop) carries `smoke-skip`. The script's docstring has the details.
