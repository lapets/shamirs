from setuptools import setup

setup(
    name             = 'shamirs',
    version          = '0.1.0.0',
    packages         = ['shamirs',],
    install_requires = ['lagrange',],
    license          = 'MIT',
    url              = 'https://github.com/lapets/lagrange',
    author           = 'Andrei Lapets',
    author_email     = 'a@lapets.io',
    description      = 'Python library with a minimal native implementation of Shamir\'s Secret Sharing algorithm.',
    long_description = open('README.rst').read(),
    test_suite       = 'nose.collector',
    tests_require    = ['nose'],
)
