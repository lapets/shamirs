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

MODULUS_DEFAULT = (2 ** 127) - 1
"""
Default prime modulus (equivalent to ``(2 ** 127) - 1``) that is used for
creating secret shares if a prime modulus is not specified explicitly.
"""

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

class share:
    """
    Data structure for representing an individual secret share. Normally, the
    :obj:`shares` function should be used to construct a sequence of :obj:`share`
    objects.

    >>> isinstance(shares(1, 3, modulus=31)[0], share)
    True
    >>> len(shares(1, 3, modulus=31))
    3
    >>> interpolate(shares(123, 12, modulus=15485867))
    123
    >>> interpolate(shares(2**100, 100)) == 2**100
    True

    It must be possible to represent the index integer using 32 bits. There is no
    bound on the size of the value.

    >>> share(4294967296, 123)
    Traceback (most recent call last):
      ...
    ValueError: index must be an integer that can be represented using at most 32 bits
    """
    def __init__(self: share, index: int, value: int, modulus: Optional[int] = MODULUS_DEFAULT):
        """
        Create a share instance according to the supplied parameters.
        """
        if index > 4294967295:
            raise ValueError(
                'index must be an integer that can be represented using at most 32 bits'
            )

        self.index = index
        self.value = value
        self.modulus = modulus

    @staticmethod
    def from_bytes(bs: Union[bytes, bytearray]) -> share:
        """
        Convert a secret share represented as a bytes-like object
        into a :obj:`share` object.

        >>> s = share.from_bytes(bytes.fromhex('7b00000002000000c801fd03'))
        >>> (s.index, s.value, s.modulus)
        (123, 456, 1021)
        >>> s = share.from_bytes(share(1, 2**100).to_bytes())
        >>> (s.index, s.value) == (1, 2**100)
        True
        """
        length = int.from_bytes(bs[4: 8], 'little')
        return share(
            int.from_bytes(bs[:4], 'little'),
            int.from_bytes(bs[8: (8 + length)], 'little'),
            int.from_bytes(bs[(8 + length):], 'little')
        )

    @staticmethod
    def from_base64(s: str) -> share:
        """
        Convert a secret share represented as a Base64 encoding of
        a bytes-like object into a :obj:`share` object.

        >>> s = share.from_base64('ewAAAAIAAADIAf0D')
        >>> (s.index, s.value, s.modulus)
        (123, 456, 1021)
        >>> s = share.from_base64(share(3, 2**100).to_base64())
        >>> (s.index, s.value) == (3, 2**100)
        True
        """
        return share.from_bytes(base64.standard_b64decode(s))

    def to_bytes(self: share) -> bytes:
        """
        Return a bytes-like object that encodes this :obj:`share` object.

        >>> share(123, 456, 1021).to_bytes().hex()
        '7b00000002000000c801fd03'
        >>> s = share.from_bytes(share(3, 2**100).to_bytes())
        >>> (s.index, s.value) == (3, 2**100)
        True
        """
        length = (self.modulus.bit_length() + 7) // 8
        return (
            int(self.index).to_bytes(4, 'little') + \
            int(length).to_bytes(4, 'little') + \
            int(self.value).to_bytes(length, 'little') + \
            int(self.modulus).to_bytes(length, 'little')
        )

    def to_base64(self: share) -> str:
        """
        Return a Base64 string representation of this :obj:`share` object.

        >>> share(123, 456, 1021).to_base64()
        'ewAAAAIAAADIAf0D'
        >>> s = share.from_base64(share(3, 2**100).to_base64())
        >>> (s.index, s.value) == (3, 2**100)
        True
        """
        return base64.standard_b64encode(self.to_bytes()).decode('utf-8')

def shares(
        value: int,
        quantity: int,
        modulus: Optional[int] = MODULUS_DEFAULT,
        threshold: Optional[int] = None
    ) -> Sequence[share]:
    """
    Transforms an integer value into the specified number of secret shares, with
    recovery of the original value possible using the returned sequence of secret
    shares (via the :obj:`interpolate` function).

    :param value: Integer value to be split into secret shares.
    :param quantity: Number of secret shares (at least two) to construct
        and return.
    :param modulus: Prime modulus corresponding to the finite field used for
        creating secret shares.
    :param threshold: Minimum number of shares that will be required to
        reconstruct a value.

    >>> len(shares(1, 3, modulus=31))
    3
    >>> len(shares(17, 10, modulus=41))
    10
    >>> len(shares(123, 100))
    100

    Attempts to transform a value that is greater than the supplied prime
    modulus raise an exception.

    >>> shares(256, 3, modulus=31)
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

    Requesting fewer shares than needed to reconstruct is permitted (but a
    warning is issued).

    >>> len(shares(1, quantity=3, modulus=11, threshold=7))
    3

    Requesting a larger set of shares than is necessary to reconstruct the
    original value is permitted.

    >>> len(shares(1, quantity=7, modulus=11, threshold=3))
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

    if not isinstance(modulus, int):
        raise TypeError('prime modulus must be an integer')

    if modulus < 2:
        raise ValueError('prime modulus must be at least 2')

    if value >= modulus:
        raise ValueError('value cannot be greater than the prime modulus')

    # Use the maximum threshold if one is not specified.
    threshold = threshold or quantity
    if threshold > quantity:
        warnings.warn(
            'quantity of shares should be at least the threshold to be reconstructable'
        )

    # Add the base coefficient.
    coefficients = [value] + [_randint(modulus - 1) for _ in range(1, threshold - 1)]

    # Compute each share value such that ``shares[i] = f(i)`` if the polynomial
    # is ``f``.
    shares_ = [
        sum(
            c_j * i ** j % modulus
            for j, c_j in enumerate(coefficients)
        ) % modulus
        for i in range(1, quantity + 1)
    ]

    # Embed each shares index (x-coordinate) by shifting right and using the new lowest 32-bits.
    shares_ = [share(index + 1, value, modulus) for (index, value) in enumerate(shares_)]

    return shares_

def interpolate(shares: Iterable[share], threshold: int = None) -> int: # pylint: disable=W0621
    """
    Reassemble an integer value from a sequence of secret shares using
    Lagrange interpolation (via the :obj:`~lagrange.lagrange.interpolate` function
    exported by the `lagrange <https://pypi.org/project/lagrange>`__ library).

    :param shares: Iterable of shares from which to reconstruct a value.
    :param threshold: Minimum number of shares that will be required to
        reconstruct a value.

    >>> interpolate(shares(5, 3, modulus=31))
    5
    >>> interpolate(shares(123, 12))
    123

    The appropriate order for the secret shares is already encoded in the
    individual :obj:`share` instances (assuming they were created using
    the :obj:`shares` function). Thus, they can be supplied in any order.

    >>> interpolate(reversed(shares(123, 12)))
    123

    If the threshold is known to be different than the number of shares,
    it should be specified as such. In the example below, the value 123
    was shared with twenty parties such that at least twelve of them
    must collaborate to reconstruct the value.

    >>> interpolate(shares(123, 20, 1223, 12)[:12], 12) # Use first twelve shares.
    123
    >>> interpolate(shares(123, 20, 1223, 12)[20-12:], 12) # Use last twelve shares.
    123
    >>> interpolate(shares(123, 20, 1223, 12)[:15], 12)  # Use first fifteen shares.
    123
    >>> interpolate(shares(123, 20, 1223, 12)[:11], 12)  # Try using only eleven shares.
    Traceback (most recent call last):
      ...
    ValueError: not enough points for a unique interpolation

    Invocations with invalid parameter values raise exceptions.

    >>> interpolate([1, 2, 3])
    Traceback (most recent call last):
      ...
    TypeError: input must contain share objects
    >>> interpolate(shares(123, 3, 1223) + shares(123, 3, 1021))
    Traceback (most recent call last):
      ...
    ValueError: all shares must have the same modulus
    """
    shares = list(shares) # Store shares for reuse, even if an iterable is supplied.
    if not all (isinstance(s, share) for s in shares):
        raise TypeError('input must contain share objects')

    moduli = [s.modulus for s in shares]
    if len(set(moduli)) > 1:
        raise ValueError('all shares must have the same modulus')

    return lagrange.interpolate(
        [(s.index, s.value) for s in shares],
        moduli[0],
        (threshold or len(shares)) - 1
    )

if __name__ == '__main__': # pragma: no cover
    doctest.testmod()
