"""
Minimal pure-Python implementation of
`Shamir's Secret Sharing scheme <https://en.wikipedia.org/wiki/Shamir%27s_Secret_Sharing>`__.
"""
from __future__ import annotations
import doctest
import warnings
from typing import Union, Optional, Sequence
from collections.abc import Iterable
import base64
import secrets
import lagrange

def _randint(bound: int) -> int:
    """
    Generate a random integer according to an approximately uniform distribution
    via rejection sampling.
    """
    length = 1 + (bound.bit_length() // 8)

    value = int.from_bytes(secrets.token_bytes(length), 'little')
    while value >= bound:
        value = int.from_bytes(secrets.token_bytes(length), 'little')

    return value

class share(int):
    """
    Data structure for representing an individual secret share.
    Normally, the :obj:`shares` function should be used to construct a sequence
    of :obj:`share` objects.

    >>> isinstance(shares(1, 3, prime=31)[0], share)
    True
    >>> len(shares(1, 3, prime=31))
    3
    >>> interpolate(shares(123, 12, prime=15485867), prime=15485867)
    123
    >>> interpolate(shares(2**100, 100)) == 2**100
    True
    """
    @staticmethod
    def from_bytes(bs: Union[bytes, bytearray]) -> share:
        """
        Convert a secret share represented as a bytes-like object
        into a :obj:`share` object.

        >>> share.from_bytes(bytes([1, 123]))
        31489
        >>> share.from_bytes(share(2**100).to_bytes()) == 2**100
        True
        """
        return int.from_bytes(bs, 'little')

    @staticmethod
    def from_base64(s: str) -> share:
        """
        Convert a secret share represented as a Base64 encoding of
        a bytes-like object into a :obj:`share` object.

        >>> share.from_base64('HgEA')
        286
        >>> share.from_base64(share(2**100).to_base64()) == 2**100
        True
        """
        return share.from_bytes(base64.standard_b64decode(s))

    def to_bytes(self: share) -> bytes:
        """
        Return a bytes-like object that encodes this :obj:`share` object.

        >>> share(123).to_bytes().hex()
        '7b'
        >>> share.from_bytes(share(2**100).to_bytes()) == 2**100
        True
        """
        return int(self).to_bytes((self.bit_length() + 7) // 8, 'little')

    def to_base64(self: share) -> str:
        """
        Return a Base64 string representation of this :obj:`share` object.

        >>> share(456).to_base64()
        'yAE='
        >>> share.from_base64(share(2**100).to_base64()) == 2**100
        True
        """
        return base64.standard_b64encode(self.to_bytes()).decode('utf-8')

def shares(
        value, quantity: int, prime: Optional[int] = None, threshold: Optional[int] = None
    ) -> Sequence[share]:
    """
    Transforms an integer into the specified number of secret shares, with recovery
    of the original value possible using the returned sequence of secret shares (via
    the :obj:`interpolate` function).

    >>> len(shares(1, 3, prime=31))
    3
    >>> len(shares(17, 10, prime=41))
    10
    >>> len(shares(123, 100))
    100

    Attempts to transform a value that is greater than the supplied prime
    modulus raise an exception.

    >>> shares(256, 3, prime=31)
    Traceback (most recent call last):
      ...
    ValueError: value cannot be greater than the prime modulus

    Other invocations with invalid parameter values also raise exceptions.

    >>> shares('abc', 3, 17)
    Traceback (most recent call last):
      ...
    TypeError: value must be an integer
    >>> shares(1, 'abc', 17)
    Traceback (most recent call last):
      ...
    TypeError: quantity of shares must be an integer
    >>> shares(1, 3, 'abc')
    Traceback (most recent call last):
      ...
    TypeError: prime modulus must be an integer
    >>> shares(-2, 3, 17)
    Traceback (most recent call last):
      ...
    ValueError: value must be a nonnegative integer
    >>> shares(1, 1, 17)
    Traceback (most recent call last):
      ...
    ValueError: quantity of shares must be at least 2
    >>> shares(1, 2**32, 17)
    Traceback (most recent call last):
      ...
    ValueError: quantity of shares must be an integer that can be represented using at most 32 bits
    >>> shares(1, 3, 1)
    Traceback (most recent call last):
      ...
    ValueError: prime modulus must be at least 2

    It is allowed to ask for fewer shares than needed to reconstruct, but the library will raise a
    warning: UserWarning: quantity of shares should be at least the threshold to be reconstructable.
    >>> len(shares(1, 3, 11, 7))
    3

    One may also ask for a larger set of shares than necessary to later reconstruct.
    >>> len(shares(1, 7, 11, 3))
    7
    """
    if not isinstance(value, int):
        raise TypeError('value must be an integer')

    if value < 0:
        raise ValueError('value must be a nonnegative integer')

    if not isinstance(quantity, int):
        raise TypeError('quantity of shares must be an integer')

    if quantity < 2:
        raise ValueError('quantity of shares must be at least 2')

    if quantity >= 2 ** 32:
        raise ValueError(
            'quantity of shares must be an integer that can be represented using at most 32 bits'
        )

    if prime is not None:
        if not isinstance(prime, int):
            raise TypeError('prime modulus must be an integer')
        if prime < 2:
            raise ValueError('prime modulus must be at least 2')
        if value >= prime:
            raise ValueError('value cannot be greater than the prime modulus')

    # Use the maximum threshold if one is not specified.
    threshold = threshold or quantity
    if threshold > quantity:
        warnings.warn('quantity of shares should be at least the threshold to be reconstructable')

    # Use a default prime value if one is not specified.
    prime = (2 ** 127) - 1 if prime is None else prime

    # Add the base coefficient.
    coefficients = [value] + [_randint(prime - 1) for _ in range(1, threshold-1)]

    # Compute each share value such that ``shares[i] = f(i)`` if the polynomial
    # is ``f``.
    shares_ = [
        sum(
            c_j * i ** j % prime
            for j, c_j in enumerate(coefficients)
        ) % prime
        for i in range(1, quantity+1)
    ]

    # Embed each shares index (x-coordinate) by shifting right and using the new lowest 32-bits.
    shares_ = [share((share_ * (2 ** 32)) + i) for i, share_ in enumerate(shares_)]

    return shares_

def interpolate(shares: Iterable[share], prime: Optional[int] = None, threshold=None) -> int: # pylint: disable=W0621
    """
    Reassemble an integer value from a sequence of secret shares using
    Lagrange interpolation (via the :obj:`~lagrange.lagrange.interpolate` function
    exported by the `lagrange <https://pypi.org/project/lagrange/>`_ library).

    >>> interpolate(shares(5, 3, prime=31), 31)
    5
    >>> interpolate(shares(123, 12, prime=15485867), prime=15485867)
    123
    >>> interpolate(shares(123, 12))
    123

    The appropriate order for the secret shares is already encoded in the
    individual :obj:`share` instances (assuming they were created using
    the :obj:`shares` function). Thus, they can be supplied in any order.

    >>> interpolate(reversed(shares(123, 12)))
    123

    If the threshold is known to be different than the number of shares,
    it should be specified as such.  For example, there is a secret, 123,
    that was shared to twenty parties such that at least twelve of them
    are needed to collaborate in reconstructing the secret.
    >>> interpolate(shares(123, 20, 1223, 12)[:12], 1223, 12)  # use the first twelve shares
    123
    >>> interpolate(shares(123, 20, 1223, 12)[20-12:], 1223, 12)  # use the last twelve shares
    123
    >>> interpolate(shares(123, 20, 1223, 12)[:15], 1223, 12)  # use the first fifteen shares
    123
    >>> interpolate(shares(123, 20, 1223, 12)[:11], 1223, 12)  # try to use only eleven shares
    Traceback (most recent call last):
      ...
    ValueError: not enough points for a unique interpolation

    Invocations with invalid parameter values raise exceptions.

    >>> interpolate([1, 2, 3], prime=17)
    Traceback (most recent call last):
      ...
    TypeError: input must contain share objects
    >>> interpolate(shares(123, 12), prime='abc')
    Traceback (most recent call last):
      ...
    TypeError: prime modulus must be an integer
    >>> interpolate(shares(123, 12), prime=-2)
    Traceback (most recent call last):
      ...
    ValueError: prime modulus must be at least 2
    """
    shares = list(shares) # Store shares for reuse, even if an iterable is supplied.
    if not all (isinstance(s, share) for s in shares):
        raise TypeError('input must contain share objects')

    if prime is not None:
        if not isinstance(prime, int):
            raise TypeError('prime modulus must be an integer')
        if prime < 2:
            raise ValueError('prime modulus must be at least 2')

    # Use a default prime value if one is not specified.
    prime = (2 ** 127) - 1 if prime is None else prime

    return lagrange.interpolate(
        [(1 + (s % (2 ** 32)), s // (2 ** 32)) for s in shares],
        prime,
        (threshold or len(shares))-1
    )

if __name__ == "__main__": # pragma: no cover
    doctest.testmod()
