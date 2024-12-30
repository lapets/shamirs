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

.. |secrets_token_bytes| replace:: ``secrets.token_bytes``
.. _secrets_token_bytes: https://docs.python.org/3/library/secrets.html#secrets.token_bytes

This library provides functions and data structures for computing secret shares given an integer input value and for reassembling an integer from its corresponding secret shares via Lagrange interpolation over finite fields (according to `Shamir's secret sharing scheme <https://en.wikipedia.org/wiki/Shamir%27s_secret_sharing>`__). The built-in |secrets_token_bytes|_ function and rejection sampling are used to generate random coefficients. The `lagrange <https://pypi.org/project/lagrange>`__ library is used for Lagrange interpolation.

Installation and Usage
----------------------
This library is available as a `package on PyPI <https://pypi.org/project/shamirs>`__:

.. code-block:: bash

    python -m pip install shamirs

The library can be imported in the usual way:

.. code-block:: python

    import shamirs

Examples
^^^^^^^^
The library provides functions for transforming a nonnegative integer value into a number of secret shares and for reassembling those shares back into the value they represent:

.. code-block:: python

    >>> ss = shamirs.shares(123, quantity=3)
    >>> len(ss)
    3
    >>> shamirs.interpolate(ss)
    123
    >>> ss = shamirs.shares(456, quantity=20, modulus=15485867, threshold=10)
    >>> shamirs.interpolate(ss[5:15], threshold=10)
    456

Addition of shares and multiplication of shares by a scalar are both supported:

.. code-block:: python

    >>> (r, s, t) = shamirs.shares(123, 3)
    >>> (u, v, w) = shamirs.shares(456, 3)
    >>> shamirs.interpolate([r + u, s + v, t + w])
    579
    >>> (r, s, t) = shamirs.shares(123, 3)
    >>> r = r * 2
    >>> s = s * 2
    >>> t = t * 2
    >>> shamirs.interpolate([r, s, t])
    246

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
    python -m pytest -W ignore::UserWarning

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
