from setuptools import setup


version = "0.10.1"

setup(
    name='hyperdash',
    packages=['hyperdash', 'hyperdash_cli'],
    install_requires=[
        'requests',
        'six>=1.10.0',
        'python-slugify',
    ],
    entry_points={
        'console_scripts': ['hyperdash = hyperdash_cli.cli:main']
    },
    version=version,
    description='Hyperdash.io CLI and SDK',
    author='Hyperdash',
    author_email='support@hyperdash.io',
    url='https://hyperdash.io',
)
