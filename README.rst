GHIA
====

This project is a solution to a homework assignment, hence the garbage code quality

The app is used to automatically assign issues to specific users based on the content of a github issue.
To determine if an issue can be assigned to a user, users are associated with regular expressions tied to a specific part of an issue body that will be checked.
For example: any issue containing the word alicorn in its title goes to `M.A.Larson <https://mlp.fandom.com/wiki/M._A._Larson>`_
A user is considered assignable if any one of the associated regexps matches.
If no users are considered assignable, the issue can be given a fallback label.

Generating the documentation
============================

For it to work, you'll need to get all the required packages from requirements.txt and docs/requirements.txt.
This can be done by running `pip install -r path/to/requirements.txt`
After you gathered all the dependencies go to the docs dir, `cd docs`, then call `make html`.
Then open the index.html found in the _build directory to view the docummentation.

For running the doctests use `make doctest` in the docs directory.
