import os
from setuptools import setup

with open(os.path.join('hyperdash', 'VERSION'), 'r') as version_file:
    VERSION = version_file.read().strip()

with open('PYPI_README.rst', 'r') as readme_file:
    LONG_DESCRIPTION = readme_file.read().strip()

setup(
    name='hyperdash',
    packages=['hyperdash', 'hyperdash_cli'],
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
    package_data={'': ['VERSION']},
    version=VERSION,
    description='Hyperdash.io CLI and SDK',
    long_description=LONG_DESCRIPTION,
    author='Hyperdash',
    author_email='support@hyperdash.io',
    url='https://hyperdash.io',
)
