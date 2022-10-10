# Contributing to stereotype

We will welcome your contributions and any other efforts to make stereotype better!

## Reporting issues
If you find a bug, suspect one, find some error messages or documentation confusing, please let us know using
[GitHub Issues](https://github.com/petee-d/stereotype/issues). Make sure to include the following except a description
of the issue, where relevant:
* the version you are using
* ideally a runnable code example that showcases the issue
* explanation of what behavior you expect

## Requesting features
We accept feature requests (also submitted using [GitHub Issues](https://github.com/petee-d/stereotype/issues)),
although please note our goal is to keep stereotype fast and simple, trying to do more with less.
Things likely to be used by many stereotype users could be implemented by maintainers.
If the popularity of the proposed is questionable, but it wouldn't go against the principles above,
you can still implement it yourself!

## Contributing with pull requests
We encourage you to get your hands dirty (not really, the codebase is nice!) and submit pull requests for the changes
you would like to see.

For major changes, we recommend opening an issue and discussing the proposed change with maintainers first -
this will help align our existing efforts with yours, get you some useful pointers on how to implement the change
in the best possible way, or maybe even reveal reasons why the change may not be the best idea.

### Setting up the repository
* Ensure you have Python 3.8 (or above), `virtualenv`, `git` and `make`
* Fork the repository, clone it locally and checkout a new branch from `master`
* Since stereotype maintains compatibility with Python 3.8 and above, it's best to use that one
  ```shell
  virtualenv -p python3.8 venv
  source venv/bin/activate
  ```
* Currently, stereotype has no hard dependencies. In order to run the full test suite, however, you need to install all
  the optional dependencies
  ```shell
  make install
  ```
* Now the fun part - **make your changes**
* Simulate CI checks locally
  ```shell
  make  # Will run both `make lint` and `make test-coverage` with coverage
  ```
* Commit (ideally please suffix the commits with GitHub issue ID, like ` (#123)`), push and create a pull request

### Contribution recommendations
Please, make sure your contribution satisfies the following recommendations:

* **Test coverage** - stereotype must retain 100% line coverage after your changes; both happy paths and edge cases
  should be covered
* **Type hints** - all function arguments should have type hints
* **Code documentation** - document what you can with good function and variable names, use comments to explain ideas;
  public APIs should pretty much always have docstrings that include parameters
* **External documentation** - if your contribution deserves a mention in the documentation, please do so
* **Changelog** - all but the most trivial changes deserve a mention in `CHANGELOG.md`, feel free to create a section
  for the future tag if none is there yet
