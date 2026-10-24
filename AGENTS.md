# Agent notes

## Running tests

    uvx --with pytest-django --with pytest-cov --with django --with-editable . pytest tests

`tox` runs the full matrix. The pre-commit hooks (ruff, ruff format, etc.) run on commit.

## Commits

Commit feature by feature. Keep commit messages minimal and don't repeat
what's visible in the diff itself.

Don't add attribution (no `Co-Authored-By` lines or "Generated with" footers)
to commit messages or pull request descriptions.
