from setuptools import setup


version = "0.1.0"

with open('README.md', 'rb') as f:
    long_descr = f.read().decode('utf-8')

setup(
    name='hyperdash',
    packages=['cli', 'sdk'],
    install_requires=[
        'ws4py',
        'six'
    ],
    entry_points={
        'console_scripts': ['hyperdash = cli.cli:main']
    },
    version=version,
    description='Hyperdash.io CLI and SDK',
    long_description=long_descr,
    author='Hyperdash',
    author_email='support@hyperdash.io',
    url='https://hyperdash.io',
)
