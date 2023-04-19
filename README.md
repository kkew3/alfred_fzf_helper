# Introduction

Helper functions that enable fuzzy search via [`fzf`](https://github.com/junegunn/fzf) in Alfred 5.
Also supports command mode within query, which search for commands embedded in the query.

For example usage, see `test_fzf_filter()` test cases in file `alfzf.py`.

# Comparing with [`alfred-fuzzy`](https://github.com/deanishe/alfred-fuzzy)

While being less convenient than `alfred-fuzzy`, this library is meant to bring more flexibility to the user.

# Test

To run the tests, you will need `pytest`, and then run `pytest alfzf.py test_pressure_fzf_filter.py`.

# Performance

See files under directory `benchmark`.
To run `test_pressure_fzf_filter.py` (which generates content under `benchmark`) on your computer, you will need

- numpy
- joblib
- matplotlib

and then run `python3 -c "import test_pressure_fzf_filter as tp; tp.make_table()"`.
