# Agent notes

## Running tests

    uvx --with pytest-django --with pytest-cov --with django --with-editable . pytest tests

`tox` runs the full matrix. The pre-commit hooks (ruff, ruff format, etc.) run on commit.

## Commits

Don't add attribution (no `Co-Authored-By` lines or "Generated with" footers)
to commit messages or pull request descriptions.
