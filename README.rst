=======
shamirs
=======

Minimal pure-Python implementation of Shamir's Secret Sharing scheme.

|pypi| |readthedocs| |actions| |coveralls|

.. |pypi| image:: https://badge.fury.io/py/shamirs.svg
   :target: https://badge.fury.io/py/shamirs
   :alt: PyPI version and link.

.. |readthedocs| image:: https://readthedocs.org/projects/shamirs/badge/?version=latest
   :target: https://shamirs.readthedocs.io/en/latest/?badge=latest
   :alt: Read the Docs documentation status.

.. |actions| image:: https://github.com/lapets/shamirs/workflows/lint-test-cover-docs/badge.svg
   :target: https://github.com/lapets/shamirs/actions/workflows/lint-test-cover-docs.yml
   :alt: GitHub Actions status.

.. |coveralls| image:: https://coveralls.io/repos/github/lapets/shamirs/badge.svg?branch=main
   :target: https://coveralls.io/github/lapets/shamirs?branch=main
   :alt: Coveralls test coverage summary.

Purpose
-------

.. |secrets_token_bytes| replace:: ``secrets.token_bytes``
.. _secrets_token_bytes: https://docs.python.org/3/library/secrets.html#secrets.token_bytes

This library provides functions and data structures for computing secret shares given an integer input value and for reassembling an integer from its corresponding secret shares via Lagrange interpolation over finite fields (according to `Shamir's Secret Sharing scheme <https://en.wikipedia.org/wiki/Shamir%27s_Secret_Sharing>`__). The built-in |secrets_token_bytes|_ function and rejection sampling are used to generate random coefficients. The `lagrange <https://pypi.org/project/lagrange>`__ library is used for Lagrange interpolation.

Installation and Usage
----------------------
This library is available as a `package on PyPI <https://pypi.org/project/shamirs>`__::

    python -m pip install shamirs

The library can be imported in the usual way::

    import shamirs

Examples
^^^^^^^^
The library provides functions for transforming a positive integer value into a number of secret shares and for reassembling those shares back into the value they represent::

    >>> ss = shamirs.shares(123, 3)
    >>> shamirs.interpolate(ss)
    123
    >>> ss = shamirs.shares(456, 77, prime=15485867)
    >>> shamirs.interpolate(ss, prime=15485867)
    456

Development
-----------
All installation and development dependencies are managed using `setuptools <https://pypi.org/project/setuptools>`__ and are fully specified in ``setup.py``. The ``extras_require`` parameter is used to `specify optional requirements <https://setuptools.pypa.io/en/latest/userguide/dependency_management.html#optional-dependencies>`__ for various development tasks. This makes it possible to specify additional options (such as ``docs``, ``lint``, and so on) when performing installation using `pip <https://pypi.org/project/pip>`__::

    python -m pip install .[docs,lint]

Documentation
^^^^^^^^^^^^^
.. include:: toc.rst

The documentation can be generated automatically from the source files using `Sphinx <https://www.sphinx-doc.org>`__::

    python -m pip install .[docs]
    cd docs
    sphinx-apidoc -f -E --templatedir=_templates -o _source .. ../setup.py && make html

Testing and Conventions
^^^^^^^^^^^^^^^^^^^^^^^
All unit tests are executed and their coverage is measured when using `pytest <https://docs.pytest.org>`__ (see ``setup.cfg`` for configuration details)::

    python -m pip install .[test]
    python -m pytest -W ignore::UserWarning

Alternatively, all unit tests are included in the module itself and can be executed using `doctest <https://docs.python.org/3/library/doctest.html>`__::

    python shamirs/shamirs.py -v

Style conventions are enforced using `Pylint <https://www.pylint.org>`__::

    python -m pip install .[lint]
    python -m pylint shamirs

Contributions
^^^^^^^^^^^^^
In order to contribute to the source code, open an issue or submit a pull request on the `GitHub page <https://github.com/lapets/shamirs>`__ for this library.

Versioning
^^^^^^^^^^
Beginning with version 1.0.0, the version number format for this library and the changes to the library associated with version number increments conform with `Semantic Versioning 2.0.0 <https://semver.org/#semantic-versioning-200>`__.

Publishing
^^^^^^^^^^
This library can be published as a `package on PyPI <https://pypi.org/project/shamirs>`__ by a package maintainer. First, install the dependencies required for packaging and publishing::

    python -m pip install .[publish]

Remove any old build/distribution files. Then, package the source into a distribution archive using the `wheel <https://pypi.org/project/wheel>`__ package::

    rm -rf dist *.egg-info
    python setup.py sdist bdist_wheel

Finally, upload the package distribution archive to `PyPI <https://pypi.org>`__ using the `twine <https://pypi.org/project/twine>`__ package::

    python -m twine upload dist/*
