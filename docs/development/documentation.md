# Documentation

Project uses Sphinx to generate documentation from docstrings (documentation in-code) and custom pages written in Markdown (through the [MyST parser](https://myst-parser.readthedocs.io/en/latest/)).

## Build documentation website

To build it:

```bash
# install aditionnal dependencies
python -m pip install -U -r requirements/documentation.txt
# build it
sphinx-build -b html docs docs/_build
# optimized (quiet, multiprocessing, doctrees separated)
sphinx-build -b html -d docs/_build/cache -j auto -q docs docs/_build/html
```

Open `docs/_build/index.html` in a web browser.

## Write documentation using live render

```bash
sphinx-autobuild -b html -d docs/_build/cache docs/ docs/_build
```

Open <http://localhost:8000> in a web browser to see the HTML render updated when a file is saved.
