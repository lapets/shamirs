=======
shamirs
=======

Minimal pure-Python implementation of `Shamir's secret sharing scheme <https://en.wikipedia.org/wiki/Shamir%27s_secret_sharing>`__.

|pypi| |readthedocs| |actions| |coveralls|

.. |pypi| image:: https://badge.fury.io/py/shamirs.svg#
   :target: https://badge.fury.io/py/shamirs
   :alt: PyPI version and link.

.. |readthedocs| image:: https://readthedocs.org/projects/shamirs/badge/?version=latest
   :target: https://shamirs.readthedocs.io/en/latest/?badge=latest
   :alt: Read the Docs documentation status.

.. |actions| image:: https://github.com/lapets/shamirs/workflows/lint-test-cover-docs/badge.svg#
   :target: https://github.com/lapets/shamirs/actions/workflows/lint-test-cover-docs.yml
   :alt: GitHub Actions status.

.. |coveralls| image:: https://coveralls.io/repos/github/lapets/shamirs/badge.svg?branch=main
   :target: https://coveralls.io/github/lapets/shamirs?branch=main
   :alt: Coveralls test coverage summary.

Purpose
-------

.. |secrets_randbelow| replace:: ``secrets.randbelow``
.. _secrets_randbelow: https://docs.python.org/3/library/secrets.html#secrets.randbelow

This library provides functions and data structures for computing secret shares given an integer input value and for reassembling an integer from its corresponding secret shares via Lagrange interpolation over finite fields (according to `Shamir's secret sharing scheme <https://en.wikipedia.org/wiki/Shamir%27s_secret_sharing>`__). The built-in |secrets_randbelow|_ function is used to generate random coefficients. The `lagrange <https://pypi.org/project/lagrange>`__ library is used for Lagrange interpolation.

Installation and Usage
----------------------
This library is available as a `package on PyPI <https://pypi.org/project/shamirs>`__:

.. code-block:: bash

    python -m pip install shamirs

The library can be imported in the usual manner:

.. code-block:: python

    import shamirs

Examples
^^^^^^^^

.. |shares| replace:: ``shares``
.. _shares: https://shamirs.readthedocs.io/en/4.0.0/_source/shamirs.html#shamirs.shamirs.shares

.. |interpolate| replace:: ``interpolate``
.. _interpolate: https://shamirs.readthedocs.io/en/4.0.0/_source/shamirs.html#shamirs.shamirs.interpolate

The library provides the function |shares|_ for transforming a nonnegative integer plaintext into a number of secret shares and the function |interpolate|_ for reassembling those shares back into the plaintext they represent:

.. code-block:: python

    >>> ss = shamirs.shares(123, quantity=3)
    >>> len(ss)
    3
    >>> shamirs.interpolate(ss)
    123
    >>> ss = shamirs.shares(456, quantity=20, modulus=15485867, threshold=10)
    >>> shamirs.interpolate(ss[5:15], threshold=10)
    456

.. |share| replace:: ``share``
.. _share: https://shamirs.readthedocs.io/en/4.0.0/_source/shamirs.html#shamirs.shamirs.share

.. |tuple| replace:: ``tuple``
.. _tuple: https://docs.python.org/3/library/stdtypes.html#tuple

Individual secret shares are represented using the |share|_ class. This class is derived from the |tuple|_ type and can have either two integer components (the *share index* and the *share value* that together determine the coordinates of a point on a polynomial curve) or three integer components (also including the modulus). One advantage of the two-component variant is that the memory footprint of |share|_ objects is reduced. These components can be accessed either directly via their indices or via named attributes:

.. code-block:: python

    >>> s = shamirs.share(1, 2, 3)
    >>> s.index
    1
    >>> s.value
    2
    >>> s.modulus
    3
    >>> [s[0], s[1], s[2]]
    [1, 2, 3]
    >>> int(s) # Share value.
    2

The |shares|_ function accepts an optional boolean argument ``compact``, making it possible to create secret shares that do not include the modulus component:

.. code-block:: python

    >>> shamirs.shares(123, quantity=3, modulus=1009, compact=True)
    [share(1, 649), share(2, 778), share(3, 510)]

.. |special_mod| replace:: ``__mod__``
.. _special_mod: https://shamirs.readthedocs.io/en/4.0.0/_source/shamirs.html#shamirs.shamirs.share.__mod__

It is also possible to extend a two-component |share|_ object with a modulus using the built-in modulus operator (thanks to the |special_mod|_ method):

.. code-block:: python

    >>> s = shamirs.share(1, 2)
    >>> s % 3
    share(1, 2, 3)
    >>> t = shamirs.share(1, 2)
    >>> t %= 3
    >>> t
    share(1, 2, 3)

.. |special_add| replace:: ``__add__``
.. _special_add: https://shamirs.readthedocs.io/en/4.0.0/_source/shamirs.html#shamirs.shamirs.share.__add__

.. |special_mul| replace:: ``__mul__``
.. _special_mul: https://shamirs.readthedocs.io/en/4.0.0/_source/shamirs.html#shamirs.shamirs.share.__mul__

Addition of |share|_ objects and multiplication of |share|_ objects by a scalar are both supported via special methods such as |special_add|_ and |special_mul|_ that correspond to `Python's built-in addition and multiplication operators <https://docs.python.org/3/reference/datamodel.html#emulating-numeric-types>`__:

.. code-block:: python

    >>> (r, s, t) = shamirs.shares(123, 3)
    >>> (u, v, w) = shamirs.shares(456, 3)
    >>> shamirs.interpolate([r + u, s + v, t + w])
    579
    >>> (r, s, t) = shamirs.shares(123, 3)
    >>> r *= 2
    >>> s *= 2
    >>> t *= 2
    >>> shamirs.interpolate([r, s, t])
    246

When creating secret shares for a given plaintext, the modulus can be specified explicitly or omitted. When the modulus is omitted, the default is the 128-bit modulus ``(2 ** 127) - 1``:

.. code-block:: python

    >>> (r, s, t) = shamirs.shares(123, 3)
    >>> r.modulus == (2 ** 127) - 1
    True
    >>> (r, s, t) = shamirs.shares(123, 3, modulus=1009)
    >>> r.modulus
    1009

When using |interpolate|_ to reconstruct a plaintext from compact |share|_ objects, the modulus must be specified explicitly:

.. code-block:: python

    >>> (r, s, t) = shamirs.shares(123, 3, modulus=1009, compact=True)
    >>> shamirs.interpolate([r, s, t])
    Traceback (most recent call last):
      ...
    ValueError: modulus is not found in share objects and is not provided as an argument
    >>> shamirs.interpolate([r, s, t], modulus=1009)
    123

The reconstruction threshold can also be specified explicitly or omitted. When it is omitted, the default threshold is the number of secret shares requested:

.. code-block:: python

    >>> (r, s, t) = shamirs.shares(123, 3)
    >>> shamirs.interpolate([r, s, t]) # Three shares (at threshold).
    123
    >>> shamirs.interpolate([r, s]) # Two shares (below threshold).
    119174221476707020724653887077758571505
    >>> (r, s, t) = shamirs.shares(123, 3, threshold=2)
    >>> shamirs.interpolate([r, s]) # Two shares (at threshold).
    123
    >>> shamirs.interpolate([s, t]) # Two shares (at threshold).
    123
    >>> shamirs.interpolate([r, t]) # Two shares (at threshold).
    123

The threshold argument is never required when invoking |interpolate|_, but it can reduce the number of arithmetic operations performed when reconstructing a plaintext:

.. code-block:: python

    >>> ss = shamirs.shares(123, 256, threshold=2)
    >>> shamirs.interpolate(ss) # Slower.
    123
    >>> shamirs.interpolate(ss, threshold=2) # Faster.
    123

.. |add| replace:: ``add``
.. _add: https://shamirs.readthedocs.io/en/4.0.0/_source/shamirs.html#shamirs.shamirs.add

.. |mul| replace:: ``mul``
.. _mul: https://shamirs.readthedocs.io/en/4.0.0/_source/shamirs.html#shamirs.shamirs.mul

To facilitate rapid prototyping and assembly of concise tests, the |add|_ and |mul|_ helper functions are provided for performing addition and scalar multiplication operations involving collections of shares:

.. code-block:: python

    >>> ss = shamirs.shares(123, 3)
    >>> ts = shamirs.shares(456, 3)
    >>> shamirs.interpolate(shamirs.add(ss, ts))
    579
    >>> shamirs.interpolate(shamirs.mul(ss, 2))
    246

These methods can also be used instead of built-in arithmetic operators when working with |share|_ objects that have no modulus component:

.. code-block:: python

    >>> (r, s, t) = shamirs.shares(123, 3, modulus=1009, compact=True)
    >>> (u, v, w) = shamirs.shares(456, 3, modulus=1009, compact=True)
    >>> shamirs.interpolate(
    ...     [
    ...         shamirs.add(r, u, modulus=1009),
    ...         shamirs.add(s, v, modulus=1009),
    ...         shamirs.add(t, w, modulus=1009)
    ...     ],
    ...     modulus=1009
    ... )
    579
    >>> shamirs.interpolate(
    ...     [
    ...         shamirs.mul(r, 2, modulus=1009),
    ...         shamirs.mul(s, 2, modulus=1009),
    ...         shamirs.mul(t, 2, modulus=1009)
    ...     ],
    ...     modulus=1009
    ... )
    246

In addition, conversion methods for bytes-like objects and Base64 strings are included to support encoding and decoding of |share|_ objects:

.. code-block:: python

    >>> shamirs.share.from_base64('AQAAAAIAAADkAPED').to_bytes().hex()
    '0100000002000000e400f103'
    >>> [s.to_base64() for s in shamirs.shares(123, 3, 1009)]
    ['AQAAAAIAAADkAPED', 'AgAAAAIAAABRAfED', 'AwAAAAIAAADCAfED']

Development
-----------
All installation and development dependencies are fully specified in ``pyproject.toml``. The ``project.optional-dependencies`` object is used to `specify optional requirements <https://peps.python.org/pep-0621>`__ for various development tasks. This makes it possible to specify additional options (such as ``docs``, ``lint``, and so on) when performing installation using `pip <https://pypi.org/project/pip>`__:

.. code-block:: bash

    python -m pip install ".[docs,lint]"

Documentation
^^^^^^^^^^^^^
The documentation can be generated automatically from the source files using `Sphinx <https://www.sphinx-doc.org>`__:

.. code-block:: bash

    python -m pip install ".[docs]"
    cd docs
    sphinx-apidoc -f -E --templatedir=_templates -o _source .. && make html

Testing and Conventions
^^^^^^^^^^^^^^^^^^^^^^^
All unit tests are executed and their coverage is measured when using `pytest <https://docs.pytest.org>`__ (see the ``pyproject.toml`` file for configuration details):

.. code-block:: bash

    python -m pip install ".[test]"
    python -m pytest

Alternatively, all unit tests are included in the module itself and can be executed using `doctest <https://docs.python.org/3/library/doctest.html>`__:

.. code-block:: bash

    python src/shamirs/shamirs.py -v

Style conventions are enforced using `Pylint <https://pylint.readthedocs.io>`__:

.. code-block:: bash

    python -m pip install ".[lint]"
    python -m pylint src/shamirs

Contributions
^^^^^^^^^^^^^
In order to contribute to the source code, open an issue or submit a pull request on the `GitHub page <https://github.com/lapets/shamirs>`__ for this library.

Versioning
^^^^^^^^^^
Beginning with version 1.0.0, the version number format for this library and the changes to the library associated with version number increments conform with `Semantic Versioning 2.0.0 <https://semver.org/#semantic-versioning-200>`__.

Publishing
^^^^^^^^^^
This library can be published as a `package on PyPI <https://pypi.org/project/shamirs>`__ via the GitHub Actions workflow found in ``.github/workflows/build-publish-sign-release.yml`` that follows the `recommendations found in the Python Packaging User Guide <https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/>`__.

Ensure that the correct version number appears in ``pyproject.toml``, and that any links in this README document to the Read the Docs documentation of this package (or its dependencies) have appropriate version numbers. Also ensure that the Read the Docs project for this library has an `automation rule <https://docs.readthedocs.io/en/stable/automation-rules.html>`__ that activates and sets as the default all tagged versions.

To publish the package, create and push a tag for the version being published (replacing ``?.?.?`` with the version number):

.. code-block:: bash

    git tag ?.?.?
    git push origin ?.?.?
