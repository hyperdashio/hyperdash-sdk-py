HyperDash Python SDK

# How to use
1) Explain thread model
2) Explain that it captures STDOUT/STDERR
3) Explain that it explicitly manages the logging package

TODO

# Development

## Setup

1) Clone the repo
2) In the root of the SDK directory, run `virtualenv env` to create a virtual environment
3) Run `. env/bin/activate` to activate the virtual environment
4) Run `pip install --upgrade pip`
5) Run `pip install -r requirements_dev.txt` to install dependencies

### Release new version

1) Install [setuptools](https://packaging.python.org/tutorials/installing-packages/)
2) Install twine `pip install twine`
3) Increment the version in setup.py
4) Run `python setup.py sdist` to create a new tar file
5) Run `twine upload <PATH_TO_TAR_FILE>`
6) Enter credentials

## Testing
TODO


# Features

## Completed

1) Capture STDOUT/STDERR and send them to server via websockets
2) Make ServerManager resilient against network failures (buffer messages, auto retry / reconnects)
3) Basic plumbing for logging
4) Support for retrieving API key via hyperdash.json, HYPERDASH_API_KEY environment variable, and custom function.
5) Sever authentication
6) Confirm python 2.xx and 3.xxx compatibility

## TODO:

- Server authentication
- Basic test suite / integration test
- Confirm python 2.xx and 3.xxx compatibility
- Ability to start / stop / restart jobs
- Hyper-parameter injection / retrieval from server
- Create logging handler to capture logs for users already using the logging package
- Thread vs Process (to support efficient job-killing)
- StringIO buffers and unicode
- Maximum log size + truncate old logs
- Local log files
- Support recursive functions
