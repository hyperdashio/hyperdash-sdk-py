# Development

## Setup

1) Clone the repo
2) In the root of the SDK directory, run `virtualenv env` to create a virtual environment
3) Run `. env/bin/activate` to activate the virtual environment
4) Run `pip install --upgrade pip`
5) Run `pip install -r requirements_dev.txt` to install dependencies

## Release new version

1) Install [setuptools](https://packaging.python.org/tutorials/installing-packages/)
2) Install twine `pip install twine`
3) Increment the version in setup.py
4) Run `python setup.py sdist` to create a new tar file
5) Run `twine upload <PATH_TO_TAR_FILE>`
6) Enter credentials
