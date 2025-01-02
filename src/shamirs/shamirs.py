"""
Minimal pure-Python implementation of
`Shamir's secret sharing scheme <https://en.wikipedia.org/wiki/Shamir%27s_secret_sharing>`__.
"""
from __future__ import annotations
import doctest
import warnings
from typing import Union, Optional, Sequence, Iterable
import base64
import secrets
import lagrange

_MODULUS_DEFAULT = (2 ** 127) - 1
"""
Default prime modulus (equivalent to ``(2 ** 127) - 1``) that is used for
creating secret shares if a prime modulus is not specified explicitly.
"""

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
    def __init__(self: share, index: int, value: int, modulus: Optional[int] = _MODULUS_DEFAULT):
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

        :param bs: Bytes-like object that is an encoding of a share instance.

        All share information (the index, the value, and the modulus) is assumed
        to be encoded (as is done by :obj:`to_bytes`).

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

        :param s: String that is a Base64 encoding of a share instance.

        All share information (the index, the value, and the modulus) is assumed
        to be encoded (as is done by :obj:`to_base64`).

        >>> s = share.from_base64('ewAAAAIAAADIAf0D')
        >>> (s.index, s.value, s.modulus)
        (123, 456, 1021)
        >>> s = share.from_base64(share(3, 2**100).to_base64())
        >>> (s.index, s.value) == (3, 2**100)
        True
        """
        return share.from_bytes(base64.standard_b64decode(s))

    def __add__(self: share, other: Union[share, int]) -> share:
        """
        Add two secret shares (represented as :obj:`share` objects) or a share
        and an integer.

        :param other: Secret share or integer value to be added to this share.

        Note that share addition must be done consistently across all shares.

        >>> (r, s, t) = shares(123, 3)
        >>> (u, v, w) = shares(456, 3)
        >>> interpolate([r + u, s + v, t + w])
        579

        The integer constant ``0`` is supported as an input to accommodate the
        base case required by the built-in :obj:`sum` function.

        >>> share(123, 456, 1021) + 0
        share(123, 456, 1021)
        >>> ts = [shares(n, quantity=3) for n in [123, 456, 789]]
        >>> interpolate([sum(ss) for ss in zip(*ts)])
        1368

        When secret shares are added, it is not possible to determine
        whether the sum of the values they represent exceeds the maximum
        value that can be represented. If the sum does exceed the value,
        then the value reconstructed from the shares will wrap around.
        This corresponds to the usual behavior of field elements under
        addition within a field.

        >>> (a, b) = shares(1020, quantity=2, modulus=1021) # One-byte integer.
        >>> (c, d) = shares(2, quantity=2, modulus=1021) # One-byte integer.
        >>> interpolate([a + c, b + d]) == (1020 + 2) % 1021 == 1
        True

        Any attempt to add secret shares that are represented using
        different finite fields -- or that have different indices --
        raises an exception.

        >>> (r, s, t) = shares(2, quantity=3, modulus=5)
        >>> (u, v, w) = shares(3, quantity=3, modulus=7)
        >>> r + u
        Traceback (most recent call last):
          ...
        ValueError: shares being added must have the same index and modulus
        >>> (r, s, t) = shares(2, quantity=3, modulus=5)
        >>> (u, v, w) = shares(3, quantity=3, modulus=5)
        >>> r + v
        Traceback (most recent call last):
          ...
        ValueError: shares being added must have the same index and modulus

        The examples below test this addition method for a range of share
        quantities and addition operation counts.

        >>> for quantity in range(2, 20):
        ...     for operations in range(2, 20):
        ...         vs = [
        ...             int.from_bytes(secrets.token_bytes(2), 'little')
        ...             for _ in range(operations)
        ...         ]
        ...         sss = [shares(v, quantity) for v in vs]
        ...         assert(interpolate([sum(ss) for ss in zip(*sss)]) == sum(vs))
        """
        if isinstance(other, int) and other == 0:
            return self

        if self.index == other.index and self.modulus == other.modulus:
            return share(
                self.index,
                (self.value + other.value) % self.modulus,
                self.modulus
            )

        raise ValueError(
            'shares being added must have the same index and modulus'
        )

    def __radd__(self: share, other: Union[share, int]) -> share:
        """
        Add two secret shares (represented as :obj:`share` objects) or a share
        and an integer.

        :param other: Secret share or integer value to be added to this share.

        Note that share addition must be done consistently across all shares.

        >>> (r, s, t) = shares(123, 3)
        >>> (u, v, w) = shares(456, 3)
        >>> interpolate([r + u, s + v, t + w])
        579

        The integer constant ``0`` is supported as an input to accommodate the
        base case required by the built-in :obj:`sum` function.

        >>> 0 + share(123, 456, 1021)
        share(123, 456, 1021)
        >>> ts = [shares(n, quantity=3) for n in [123, 456, 789]]
        >>> interpolate([sum(ss) for ss in zip(*ts)])
        1368
        """
        if isinstance(other, int) and other == 0:
            return self

        return other + self # pragma: no cover

    def __iadd__(self: share, other: Union[share, int]) -> share:
        """
        Add a secret share or an integer value to this secret share instance.

        :param other: Secret share or integer value to be added to this share.

        Note that share addition must be done consistently across all shares.

        >>> (r, s, t) = shares(123, 3)
        >>> (u, v, w) = shares(456, 3)
        >>> r += u
        >>> s += v
        >>> w += t
        >>> interpolate([r, s, w])
        579
        """
        return other + self # pragma: no cover

    def __mul__(self: share, scalar: int) -> share:
        """
        Multiply this secret share instance by an integer scalar.

        :param scalar: Scalar value by which to multiply this share.

        Note that all secret shares must be multiplied by the same integer
        scalar in order for the reconstructed value to reflect the correct
        result.

        >>> (r, s, t) = shares(123, 3)
        >>> r = r * 2
        >>> s = s * 2
        >>> t = t * 2
        >>> interpolate([r, s, t])
        246

        When secret shares are multiplied by a scalar, it is not possible to
        determine whether the result exceeds the range of values that can be
        represented. If the result does fall outside the range, then the value
        reconstructed from the shares will wrap around. This corresponds to
        the usual behavior of field elements under scalar multiplication
        within a field.

        >>> (s, t) = shares(512, quantity=2, modulus=1021)
        >>> s = s * 2
        >>> t = t * 2
        >>> interpolate([s, t]) == (512 * 2) % 1021 == 3
        True

        The scalar argument must be a nonnegative integer.

        >>> (r, s, t) = shares(123, 3)
        >>> s = s * 2.0
        Traceback (most recent call last):
          ...
        TypeError: scalar must be an integer
        >>> (r, s, t) = shares(123, 3)
        >>> s = s * -2
        Traceback (most recent call last):
          ...
        ValueError: scalar must be a nonnegative integer

        The examples below test this scalar multiplication method for a range
        of share quantities and a number of random scalar values.

        >>> for quantity in range(2, 20):
        ...     for _ in range(100):
        ...         v = int.from_bytes(secrets.token_bytes(2), 'little')
        ...         c = int.from_bytes(secrets.token_bytes(1), 'little')
        ...         ss = shares(v, quantity)
        ...         assert(interpolate([c * s for s in ss]) == c * v)
        """
        if not isinstance(scalar, int):
            raise TypeError('scalar must be an integer')

        if scalar < 0:
            raise ValueError('scalar must be a nonnegative integer')

        return share(
            self.index,
            (self.value * scalar) % self.modulus,
            self.modulus
        )

    def __rmul__(self: share, scalar: int) -> share:
        """
        Multiply this secret share instance by an integer scalar (that appears
        on the left side of the operator).

        :param scalar: Scalar value by which to multiply this share.

        Note that all secret shares must be multiplied by the same integer
        scalar in order for the reconstructed value to reflect the correct
        result.

        >>> (r, s, t) = shares(123, 3)
        >>> r = r * 2
        >>> s = s * 2
        >>> t = t * 2
        >>> interpolate([r, s, t])
        246
        """
        return self * scalar

    def __imul__(self: share, scalar: int) -> share:
        """
        Multiply this secret share instance by an integer scalar.

        :param scalar: Scalar value by which to multiply this share.

        Note that all secret shares must be multiplied by the same integer
        scalar in order for the reconstructed value to reflect the correct
        result.

        >>> (r, s, t) = shares(123, 3)
        >>> r *= 2
        >>> s *= 2
        >>> t *= 2
        >>> interpolate([r, s, t])
        246
        """
        return self * scalar

    def __int__(self: share) -> int:
        """
        Return the least nonnegative residue of the field element corresponding
        to this instance.

        >>> int(share(123, 456, 1021))
        456
        """
        return self.value % self.modulus

    def __len__(self: share) -> int:
        """
        Return the modulus corresponding to the field (within which this instance
        represents an element).

        >>> len(share(123, 456, 1021))
        1021
        """
        return self.modulus

    def to_bytes(self: share) -> bytes:
        """
        Return a bytes-like object that encodes this :obj:`share` object.

        >>> share(123, 456, 1021).to_bytes().hex()
        '7b00000002000000c801fd03'

        All share information (the index, the value, and the modulus) is encoded.

        >>> share.from_bytes(share(3, 2**100).to_bytes()).index
        3
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
        Return a Base64 string encoding of this :obj:`share` object.

        >>> share(123, 456, 1021).to_base64()
        'ewAAAAIAAADIAf0D'

        All share information (the index, the value, and the modulus) is encoded.

        >>> share.from_base64(share(3, 2**100).to_base64()).value == 2**100
        True
        """
        return base64.standard_b64encode(self.to_bytes()).decode('utf-8')

    def __str__(self: share) -> str:
        """
        Return the string representation of this :obj:`share` object.

        >>> str(share(123, 456, 1021))
        'share(123, 456, 1021)'
        """
        return 'share(' + ', '.join([
            str(self.index),
            str(self.value),
            str(self.modulus)
        ]) + ')'

    def __repr__(self: share) -> str:
        """
        Return the string representation of this :obj:`share` object.

        >>> share(123, 456, 1021)
        share(123, 456, 1021)
        """
        return str(self)

def shares(
        value: int,
        quantity: int,
        modulus: Optional[int] = _MODULUS_DEFAULT,
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

    A modulus may be supplied; it is expected (but not checked) that the supplied
    modulus is a prime number.

    >>> len(shares(123, 100))
    100
    >>> len(shares(1, 3, modulus=31))
    3
    >>> len(shares(17, 10, modulus=41))
    10

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

    # Create the coefficients.
    coefficients = [value] + [secrets.randbelow(modulus) for _ in range(1, threshold)]

    # Compute each share value such that ``shares[i] = f(i)`` if the polynomial
    # is ``f``.
    shares_ = [
        sum(
            (c_j * (i ** j)) % modulus
            for j, c_j in enumerate(coefficients)
        ) % modulus
        for i in range(1, quantity + 1)
    ]

    # Embed each shares index (x-coordinate) by shifting right and using the new lowest 32-bits.
    shares_ = [share(index + 1, value, modulus) for (index, value) in enumerate(shares_)]

    return shares_

def interpolate(
        shares: Iterable[share], # pylint: disable=redefined-outer-name
        threshold: int = None
    ) -> int:
    """
    Reassemble an integer value from a sequence of secret shares using
    Lagrange interpolation (via the :obj:`~lagrange.lagrange.interpolate` function
    exported by the `lagrange <https://pypi.org/project/lagrange>`__ library).

    :param shares: Iterable of shares from which to reconstruct a value.
    :param threshold: Minimum number of shares that will be required to
        reconstruct a value.

    The appropriate order for the secret shares is already encoded in the
    individual :obj:`share` instances (assuming they were created using
    the :obj:`shares` function). Thus, they can be supplied in any order.

    >>> interpolate(shares(5, 3, modulus=31))
    5
    >>> interpolate(shares(123, 12))
    123
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
    >>> interpolate(shares(123, 20, 1223, 12)[:15], 12) # Use first fifteen shares.
    123
    >>> interpolate(shares(123, 20, 1223, 12)[:11], 12) # Try using only eleven shares.
    Traceback (most recent call last):
      ...
    ValueError: not enough points for a unique interpolation

    Any attempt to interpolate using a threshold value that is smaller than the
    threshold value originally specified when the shares were created yields an
    arbitrary output. However, no confirmation is performed (at the time of
    interpolation) that interpolation is being performed with the correct threshold
    value.

    >>> 123 != interpolate(shares(123, 20, 2**31 - 1, 12)[:11], 11) # Try using smaller threshold.
    True
    >>> 123 != interpolate(shares(123, 20, 2**31 - 1, 2)[:1], 1) # Try using smaller threshold.
    True

    Any attempt to interpolate using a threshold value that is larger than the
    threshold value originally specified when the shares were created returns
    the original secret-shared value.

    >>> interpolate(shares(123, 20, 2**31 - 1, 12)[:13], 13) # Try using larger threshold.
    123

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
