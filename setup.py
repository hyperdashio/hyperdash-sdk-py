from setuptools import setup


version = "0.3.4"

setup(
    name='hyperdash',
    packages=['hyperdash', 'hyperdash_cli'],
    install_requires=[
        'autobahn==17.6.2',
        'certifi==2017.4.17',
        'pyOpenSSL==17.1.0',
        'requests==2.18.1'
        'service_identity==17.0.0',
        'six==1.10.0',
        'Twisted==17.5.0',
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
