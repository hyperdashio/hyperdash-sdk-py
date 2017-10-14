import os
from setuptools import setup

HYPERDASH_PACKAGE = 'hyperdash'
CLI_PACKAGE = 'hyperdash_cli'

VERSION_FILE = 'version'
PYPI_README = 'PYPI_README.rst'

with open(os.path.join(HYPERDASH_PACKAGE, 'VERSION'), 'r') as version_file:
    VERSION = version_file.read().strip()

with open(os.path.join(HYPERDASH_PACKAGE, PYPI_README), 'r') as readme_file:
    LONG_DESCRIPTION = readme_file.read().strip()

setup(
    name=HYPERDASH_PACKAGE,
    packages=[HYPERDASH_PACKAGE, CLI_PACKAGE],
    install_requires=[
        'requests',
        'six>=1.10.0',
        'python-slugify',
    ],
    entry_points={
        'console_scripts': [
            'hyperdash = hyperdash_cli.cli:main',
            'hd = hyperdash_cli.cli:main',
            ]
    },
    package_data={'': ['VERSION', PYPI_README]},
    version=VERSION,
    description='Hyperdash.io CLI and SDK',
    long_description=LONG_DESCRIPTION,
    author='Hyperdash',
    author_email='support@hyperdash.io',
    url='https://hyperdash.io',
)
