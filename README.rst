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
