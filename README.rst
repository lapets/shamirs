=======
shamirs
=======

Python library with a minimal native implementation of Shamir's Secret Sharing algorithm.

.. image:: https://badge.fury.io/py/shamirs.svg
   :target: https://badge.fury.io/py/shamirs
   :alt: PyPI version and link.

Purpose
-------
The library provides functions for computing secret shares given an integer input value, as well as for reassembling an integer from its corresponding shares using Lagrange interpolation over finite fields. The native python :code:`random.randint` function is used to generate the polynomial when creating shares.

Package Installation and Usage
------------------------------
The package is available on PyPI::

    python -m pip install shamirs

The library can be imported in the usual way::

    import shamirs

Examples
--------
The library provides functions for splitting a value into a number of shares across a number of parties, and for reassembling those share back into the value they represent::

    >>> shares = shamirs.share(5, 3, 17)
    >>> shamirs.build(shares, 17)
    5
    >>> shamirs.build(shamirs.share(123, 12, 15485867), 15485867)
    123

Documentation
-------------
.. include:: toc.rst

The documentation can be generated automatically from the source files using `Sphinx <https://www.sphinx-doc.org/>`__::

    cd docs
    python -m pip install -r requirements.txt
    sphinx-apidoc -f -E --templatedir=_templates -o _source .. ../setup.py && make html

Testing and Conventions
-----------------------
All unit tests are executed and their coverage is measured when using `pytest <https://docs.pytest.org>`__ (see ``setup.cfg`` for configuration details)::

    python -m pip install pytest pytest-cov
    python -m pytest

Alternatively, all unit tests are included in the module itself and can be executed using `doctest <https://docs.python.org/3/library/doctest.html>`__::

    python shamirs/shamirs.py -v

Style conventions are enforced using `Pylint <https://www.pylint.org>`__::

    python -m pip install pylint
    python -m pylint shamirs

Contributions
-------------
In order to contribute to the source code, open an issue or submit a pull request on the `GitHub page <https://github.com/lapets/shamirs>`__ for this library.

Versioning
----------
Beginning with version 0.2.0, the version number format for this library and the changes to the library associated with version number increments conform with `Semantic Versioning 2.0.0 <https://semver.org/#semantic-versioning-200>`__.

Publishing
----------
This library can be published as a `package on PyPI <https://pypi.org/project/shamirs>`__ by a package maintainer. First, install the dependencies required for packaging and publishing::

    python -m pip install wheel twine

Remove any old build/distribution files. Then, package the source into a distribution archive using the `wheel <https://pypi.org/project/wheel>`__ package::

    rm -rf dist *.egg-info
    python setup.py sdist bdist_wheel

Finally, upload the package distribution archive to `PyPI <https://pypi.org>`__ using the `twine <https://pypi.org/project/twine>`__ package::

    python -m twine upload dist/*
