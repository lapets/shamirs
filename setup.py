from setuptools import setup

with open('README.rst', 'r') as fh:
    long_description = fh.read().replace('.. include:: toc.rst\n\n', '')

# The lines below can be parsed by ``docs/conf.py``.
name = 'shamirs'
version = '0.2.0'

setup(
    name=name,
    version=version,
    packages=[name,],
    install_requires=[
        'lagrange~=1.0',
    ],
    license='MIT',
    url='https://github.com/lapets/lagrange',
    author='Andrei Lapets',
    author_email='a@lapets.io',
    description='Minimal pure-Python implementation of Shamir\'s Secret Sharing scheme.',
    long_description=long_description,
    long_description_content_type='text/x-rst',
)
