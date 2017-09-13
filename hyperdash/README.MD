# Development

## Setup

1) Clone the repo
2) In the root of the SDK directory, run `virtualenv env` to create a virtual environment
3) Run `. env/bin/activate` to activate the virtual environment
4) Run `pip install --upgrade pip`
5) Run `pip install -r requirements_dev.txt` to install dependencies

Alternatively if you're trying to test the CLI, or just want to use the CLI to test the SDK code, you can run `python setup.py develop` and the Hyperdash library will be installed locally so that you can test it. Once you're done developing, run `python setup.py develop --uninstall` to clean up.

## Release new version

1) Install [setuptools](https://packaging.python.org/tutorials/installing-packages/)
2) Install twine `pip install twine`
3) Increment the version in setup.py
4) Create ~/.pypirc with the following content (spacing important!):
```
[distutils]
index-servers =
  pypi

[pypi]
username: hyperdash
password: <PASSWORD_HERE>
```
5) Run `rm -rf dist` to cleanup dist folder
6) Run `python setup.py sdist` to create a new tar file
7) Run `twine upload -r pypi <PATH_TO_TAR_FILE>` to upload to pypi
8) Verify installation by running `pip install --upgrade --no-cache-dir hyperdash`
