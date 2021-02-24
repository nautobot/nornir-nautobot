# Contributing

This section describes how to install *nornir_nautobot* for development, how to run tests, and make sure you are a good contributor.

## Branches

- `main` - Reserved for current release
- `develop` - Ready to release code, bases for new PRs
- `<feature>` - Individual feature branches, should be PR'd to `develop`.

## Python Versions

This leverages Python3.6 or later. All features will be tested against 3.6 - 3.9 versions of Python.

## Versioning

This project utilizes Semver versioning. As part of PRs the maintainers should leverage Poetry versioning to support the increase in version numbers. Reference [Poetry Version Docs](https://python-poetry.org/docs/cli/#version) for more information on automatically adjusting the version.  

## Installing dependencies for local development

> These steps are also required for using the examples as provided in the repository for demonstration purposes.  

This repository uses [poetry](https://python-poetry.org/) for dependency management and [invoke](http://www.pyinvoke.org) for task execution. To see what invoke commands are available, issue the command `invoke --list`.   

Follow these steps to set up your local development environment:

```bash
# Double check your version
$ python --version
Python 3.7.7
# Activate the Poetry environment, which will auto create the virtual environment related to the project
$ poetry shell
# Install project dependencies as well as development dependencies
$ poetry install
```

When you install dependencies via Poetry you will get invoke as part of the process.

## Running tests locally

Docker images are available to provide a consistent development environment from one machine to another. The best practice recommendation is to execute two steps to test:

1. Build Docker container image (`invoke build`)
2. Execute test environment (`invoke tests`)
   1. You can execute individual tests as well by looking at the tests with the command `invoke --list`

### Build Docker container image

Invoke tasks have a task to help build the containers. Executing the task with `invoke build` will build the Docker image for testing.

### Execute tests

The Invoke task to execute the tests are then `invoke tests`. This will execute all of the linting and pytest functions on the code.

## Testing

All tests should be located within the `tests\` directory with `tests\unit` for the unit tests. Integration tests should be in the `tests\integration` directory.

### Testing - Required

The following linting tasks are required:

* [Bandit](https://bandit.readthedocs.io/en/latest/)
  * Basic security tests, should be run on Python3.6 or Python3.7
* [Black code style](https://github.com/psf/black)
  * Code formatting with version 20.8b1. There are some differences in the format between versions 19 and 20.
* [Flake8](https://flake8.pycqa.org/en/latest/)
  * Black vs Flake conflicts: When conflicts arise between Black and Flake8, Black should win and Flake8 should be configured as such
* [Pydocstyle](https://github.com/PyCQA/pydocstyle/)
* [Pylint](https://www.pylint.org)
* [Yamllint](https://yamllint.readthedocs.io)

### Tests - Interim

In the interim while the primary project is still in private access, any execution environments (pynautobot or Nautobot itself) should be packaged and stored in `tests\packages` for independent installation until the public images are available.
