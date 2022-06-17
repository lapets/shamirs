from setuptools import setup

setup(
    name='shamirs',
    version='0.2.0',
    packages=['shamirs',],
    install_requires=[
        'lagrange~=1.0',
    ],
    license='MIT',
    url='https://github.com/lapets/lagrange',
    author='Andrei Lapets',
    author_email='a@lapets.io',
    description='Minimal pure-Python implementation of Shamir\'s Secret Sharing scheme.',
    long_description=open('README.rst').read(),
)
