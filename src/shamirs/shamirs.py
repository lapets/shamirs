"""
Minimal pure-Python implementation of
`Shamir's secret sharing scheme <https://en.wikipedia.org/wiki/Shamir%27s_secret_sharing>`__.
"""
from __future__ import annotations
import doctest
from typing import Union, Optional
from collections.abc import Callable, Iterable, Sequence
import base64
import secrets
import lagrange

_MODULUS_DEFAULT: int = (2 ** 127) - 1
"""
Default prime modulus of ``(2 ** 127) - 1`` that is used for creating secret
shares if a prime modulus is not specified explicitly.

One advantage of this modulus is that all arithmetic operations involving
share values and moduli can be restricted to 128-bit integer inputs and
outputs.
"""

class share(tuple):
    """
    Data structure for representing an individual secret share. A share can
    have either two integer components (the share index and the share value
    that together determine the coordinates of a point on a polynomial curve)
    or three integer components (also including the modulus).

    >>> share(1, 123, 1009)
    share(1, 123, 1009)
    >>> share(1, 123)
    share(1, 123)

    Normally, the :obj:`shares` function should be used to construct a sequence
    of :obj:`share` objects.

    >>> isinstance(shares(1, 3, modulus=31)[0], share)
    True
    >>> len(shares(1, 3, modulus=31))
    3
    >>> interpolate(shares(123, 12, modulus=15485867))
    123
    >>> interpolate(shares(2**100, 100)) == 2**100
    True

    The index must be a positive integer that can be represented using at most
    32 bits. The value must be nonnegative and must not exceed the modulus.
    The modulus must be at least ``2``.

    >>> share(4294967296, 123, (2**127) - 1)
    Traceback (most recent call last):
      ...
    ValueError: index must be a positive integer requiring at most 32 bits
    >>> share(2, -123, (2**127) - 1)
    Traceback (most recent call last):
      ...
    ValueError: share value must be a nonnegative integer
    >>> share(2, 2000, 1009)
    Traceback (most recent call last):
      ...
    ValueError: share value must be strictly less than the prime modulus
    >>> share(2, 123, 1)
    Traceback (most recent call last):
      ...
    ValueError: prime modulus must be at least 2

    Any other attempt to supply invalid arguments raises an exception.

    >>> share('abc', 123, 1009)
    Traceback (most recent call last):
      ...
    TypeError: index must be an integer
    >>> share(2, 'abc', 1009)
    Traceback (most recent call last):
      ...
    TypeError: value must be an integer
    >>> share(2, 123, 'abc')
    Traceback (most recent call last):
      ...
    TypeError: prime modulus must be an integer
    """
    def __new__(cls: type, index: int, value: int, modulus: Optional[int] = None):
        """
        Create a secret share object according to the supplied parameters.

        :param index: Index for this Shamir's secret share (*i.e.*, the first
            coordinate in the polynomial curve point).
        :param value: Value for this Shamir's secret share (*i.e.*, the second
            coordinate in the polynomial curve point).
        :param modulus: Prime modulus representing the field within which this
            secret share resides.

        >>> share(1, 123, 1009)
        share(1, 123, 1009)

        Objects of this class are also instances of the built-in :obj:`tuple`
        type.

        >>> isinstance(share(1, 123, 1009), tuple)
        True
        """
        if not isinstance(index, int):
            raise TypeError('index must be an integer')

        if not isinstance(value, int):
            raise TypeError('value must be an integer')

        if index < 1 or index > 4294967295:
            raise ValueError(
                'index must be a positive integer requiring at most 32 bits'
            )

        if value < 0:
            raise ValueError('share value must be a nonnegative integer')

        if modulus is not None:
            if not isinstance(modulus, int):
                raise TypeError('prime modulus must be an integer')

            if modulus < 2:
                raise ValueError('prime modulus must be at least 2')

            if value >= modulus:
                raise ValueError(
                    'share value must be strictly less than the prime modulus'
                )

        return super().__new__(
            cls,
            (index, value, *([] if modulus is None else [modulus]))
        )

    @staticmethod
    def from_bytes(bs: Union[bytes, bytearray]) -> share:
        """
        Convert a secret share represented as a bytes-like object into a
        :obj:`share` object.

        :param bs: Bytes-like object that is an encoding of a secret share object.

        The index and value are assumed to be encoded (as is done by
        :obj:`to_bytes`).

        >>> s = share.from_bytes(bytes.fromhex('7b00000002000000c801fd03'))
        >>> (s.index, s.value, s.modulus)
        (123, 456, 1021)
        >>> s = share.from_bytes(share(123, 2**100, (2**127) - 1).to_bytes())
        >>> (s.index, s.value, s.modulus) == (123, 2**100, (2**127) - 1)
        True

        Encoded shares with and without a modulus are supported.

        >>> s = share.from_bytes(share(123, 2**100).to_bytes())
        >>> (s.index, s.value) == (123, 2**100)
        True
        """
        length = int.from_bytes(bs[4: 8], 'little')
        modulus_bytes = bs[(8 + length):]
        return share(
            int.from_bytes(bs[:4], 'little'),
            int.from_bytes(bs[8: (8 + length)], 'little'),
            *( # Do not decode the modulus if it is not present.
                [int.from_bytes(modulus_bytes, 'little')]
                if len(modulus_bytes) > 0 else
                []
            )
        )

    @staticmethod
    def from_base64(s: str) -> share:
        """
        Convert a secret share represented as a Base64 encoding of a bytes-like
        object into a :obj:`share` object.

        :param s: String that is a Base64 encoding of a secret share object.

        The index and value are assumed to be encoded (as is done by
        :obj:`to_base64`).

        >>> s = share.from_base64('ewAAAAIAAADIAf0D')
        >>> (s.index, s.value, s.modulus)
        (123, 456, 1021)
        >>> s = share.from_base64(share(123, 2**100, (2**127) - 1).to_base64())
        >>> (s.index, s.value, s.modulus) == (123, 2**100, (2**127) - 1)
        True

        Encoded shares with and without a modulus are supported.

        >>> s = share.from_base64(share(123, 2**100).to_base64())
        >>> (s.index, s.value) == (123, 2**100)
        True
        """
        return share.from_bytes(base64.standard_b64decode(s))

    def __getattribute__(self: share, name: str) -> int:
        """
        Allow the use of named attributes to access the components of this
        secret share object.

        :param name: Name of attribute for which to return the value.

        This method enables component retrieval via named attributes (in
        addition to index-based retrieval inherited from :obj:`tuple`).

        >>> s = share(1, 2, 3)
        >>> s.index
        1
        >>> s.value
        2
        >>> s.modulus
        3
        >>> [s[0], s[1], s[2]] # Inherited.
        [1, 2, 3]

        Any attempt to retrieve a modulus that was not supplied when the
        object was created raises an exception.

        >>> s = share(1, 2)
        >>> s.modulus
        Traceback (most recent call last):
          ...
        AttributeError: 'share' object has no attribute 'modulus'

        Other attributes of this object (excluding ``index``, ``value``, and
        ``modulus``) remain supported.

        >>> list(share(1, 2, 3).__iter__())
        [1, 2, 3]
        """
        if name == 'index':
            return self[0]

        if name == 'value':
            return self[1]

        if name == 'modulus':
            if len(self) < 3:
                raise AttributeError ("'share' object has no attribute 'modulus'")
            return self[2]

        # Allow derived types with other attributes.
        return super().__getattribute__(name)

    def __int__(self: share) -> int:
        """
        Return the least nonnegative residue of the field element corresponding
        to this secret share.

        >>> int(share(123, 456, 1021))
        456
        """
        return self.value % self.modulus

    def __mod__(self: share, modulus: int) -> share:
        """
        Return a copy of this secret share with the specified modulus component.

        :param modulus: Integer to designate as the modulus in the returned share.

        >>> share(2, 123) % 1009
        share(2, 123, 1009)

        An exception is raised if an existing modulus component is already
        present but does not match the modulus provided as an argument.

        >>> share(2, 10, 17) % 1009
        Traceback (most recent call last):
          ...
        ValueError: different modulus component already present in share
        >>> share(2, 123, 1009) % 1009 # Same modulus is permitted.
        share(2, 123, 1009)

        Any attempt to supply an invalid modulus value raises an exception
        matching the exception raised for that modulus by the :obj:`share`
        constructor.

        >>> share(2, 10) % -1
        Traceback (most recent call last):
          ...
        ValueError: prime modulus must be at least 2
        """
        if len(self) == 3 and self[2] != modulus:
            raise ValueError('different modulus component already present in share')

        return share(*self[:2], modulus)

    def __add__(self: share, other: Union[share, int]) -> share:
        """
        Add two secret shares or a secret share and the integer zero.

        :param other: Secret share or integer value to be added to this share.

        Note that share addition must be done consistently across all shares.

        >>> (r, s, t) = shares(123, 3)
        >>> (u, v, w) = shares(456, 3)
        >>> interpolate([r + u, s + v, t + w])
        579
        >>> r += u
        >>> s += v
        >>> w += t
        >>> interpolate([r, s, w])
        579

        The integer constant ``0`` is supported as an input to accommodate the
        base case required by the built-in :obj:`sum` function.

        >>> share(123, 456, 1021) + 0
        share(123, 456, 1021)
        >>> ts = [shares(n, quantity=3) for n in [123, 456, 789]]
        >>> interpolate([sum(ss) for ss in zip(*ts)])
        1368

        When shares are added, it is not possible to determine whether the
        sum of the values they represent exceeds the maximum value that can
        be represented. If the sum does exceed that value, then the plaintext
        reconstructed from the shares will wrap around the modulus. This
        matches the usual behavior of field elements under addition.

        >>> (a, b) = shares(1020, quantity=2, modulus=1021)
        >>> (c, d) = shares(2, quantity=2, modulus=1021)
        >>> interpolate([a + c, b + d]) == (1020 + 2) % 1021 == 1
        True

        Both operands must be shares that have a modulus component.

        >>> share(2, 123, 1009) + 'abc'
        Traceback (most recent call last):
          ...
        TypeError: both operands must be shares
        >>> share(1, 123) + share(2, 456, 1009)
        Traceback (most recent call last):
          ...
        ValueError: both shares must have a modulus component

        Any attempt to add shares that are represented using different finite
        fields -- or that have different indices -- raises an exception.

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

        if not isinstance(other, share):
            raise TypeError('both operands must be shares')

        if len(self) == 2 or len(other) == 2:
            raise ValueError('both shares must have a modulus component')

        # pylint: disable=comparison-with-callable # For use of ``index`` attribute.
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
        Add two secret shares or a secret share and the integer zero (that
        appears on the left side of the operator).

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

    def __mul__(self: share, scalar: int) -> share:
        """
        Multiply this secret share by an integer scalar.

        :param scalar: Integer scalar by which to multiply this share.

        Note that all shares must be multiplied by the same integer scalar in
        order for the reconstructed value to reflect the correct result.

        >>> (r, s, t) = shares(123, 3)
        >>> interpolate([r * 2, s * 2, t * 2])
        246
        >>> r *= 2
        >>> s *= 2
        >>> t *= 2
        >>> interpolate([r, s, t])
        246

        When shares are multiplied by a scalar, it is not possible to determine
        whether the result exceeds the range of values that can be represented.
        If the result does fall outside the range, then the value reconstructed
        from the shares will wrap around the modulus. This matches the usual
        behavior of field elements under scalar multiplication.

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

        The share being multiplied must have a modulus component.

        >>> share(2, 123) * 3
        Traceback (most recent call last):
          ...
        ValueError: share must have a modulus component

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

        if len(self) == 2:
            raise ValueError('share must have a modulus component')

        return share(
            self.index,
            (self.value * scalar) % self.modulus,
            self.modulus
        )

    def __rmul__(self: share, scalar: int) -> share:
        """
        Multiply this secret share by an integer scalar (that appears on the
        left side of the operator).

        :param scalar: Integer scalar by which to multiply this share.

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

    def to_bytes(self: share) -> bytes:
        """
        Return a bytes-like object that encodes this :obj:`share` object.

        >>> share(123, 456, 1021).to_bytes().hex()
        '7b00000002000000c801fd03'

        All share information in this object (the index, the value, and the
        modulus) is encoded if it is present.

        >>> share.from_bytes(share(3, 2**100, (2**127) - 1).to_bytes()).index
        3
        >>> share.from_bytes(share(3, 2**100).to_bytes()).index
        3
        """
        length_bits_value = self.value.bit_length()
        length_bits_modulus = self.modulus.bit_length() if len(self) == 3 else 0
        length_bytes = (max(length_bits_value, length_bits_modulus) + 7) // 8
        return (
            int(self.index).to_bytes(4, 'little') +
            int(length_bytes).to_bytes(4, 'little') +
            int(self.value).to_bytes(length_bytes, 'little') +
            (
                bytes(0)
                if len(self) == 2 else
                int(self.modulus).to_bytes(length_bytes, 'little')
            )
        )

    def to_base64(self: share) -> str:
        """
        Return a Base64 string encoding of this :obj:`share` object.

        >>> share(123, 456, 1021).to_base64()
        'ewAAAAIAAADIAf0D'

        All share information in this object (the index, the value, and the
        modulus) is encoded if it is present.

        >>> share.from_base64(share(3, 2**100, (2**127) - 1).to_base64()).value == 2**100
        True
        >>> share.from_base64(share(3, 2**100).to_base64()).value == 2**100
        True
        """
        return base64.standard_b64encode(self.to_bytes()).decode('utf-8')

    def __str__(self: share) -> str:
        """
        Return the string representation of this :obj:`share` object.

        >>> str(share(123, 456, 1021))
        'share(123, 456, 1021)'

        The string representation omits the modulus component if this object
        does not include one.

        >>> str(share(123, 456))
        'share(123, 456)'
        """
        return 'share(' + ', '.join(
            [str(self.index), str(self.value)] +
            ([str(self.modulus)] if len(self) == 3 else [])
        ) + ')'

    def __repr__(self: share) -> str:
        """
        Return the string representation of this :obj:`share` object.

        >>> share(123, 456, 1021)
        share(123, 456, 1021)

        The string representation omits the modulus component if this object
        does not include one.

        >>> share(123, 456)
        share(123, 456)
        """
        return str(self)

def shares(
        plaintext: int,
        quantity: int,
        modulus: Optional[int] = _MODULUS_DEFAULT,
        threshold: Optional[int] = None,
        compact: bool = False
    ) -> Sequence[share]:
    """
    Transforms an integer plaintext into the specified number of secret shares,
    with recovery of the original plaintext possible using the returned sequence
    of secret shares (via the :obj:`interpolate` function).

    :param plaintext: Integer plaintext to be split into secret shares.
    :param quantity: Number of secret shares (at least two) to construct
        and return.
    :param modulus: Prime modulus corresponding to the finite field used for
        creating secret shares.
    :param threshold: Minimum number of shares that are required to reconstruct
        a plaintext.
    :param compact: Flag to indicate that the modulus should not be included
        in the returned secret shares.

    A modulus may be supplied; it is **expected but not checked** that the supplied
    modulus is a prime number.

    >>> len(shares(123, 100))
    100
    >>> len(shares(1, 3, modulus=31))
    3
    >>> len(shares(17, 10, modulus=41))
    10

    The default modulus value :obj:`_MODULUS_DEFAULT` is used if no modulus is
    specified.

    >>> (r, s, t) = shares(123, 3)
    >>> r.modulus == (2 ** 127) - 1
    True

    The reconstruction threshold can also be specified explicitly or omitted.
    When it is omitted, the default threshold is the number of secret shares
    requested.

    >>> (r, s, t) = shares(123, 3)
    >>> interpolate([r, s, t]) # Three shares (at threshold).
    123
    >>> interpolate([r, s]) == 123 # Two shares (below threshold).
    False
    >>> (r, s, t) = shares(123, 3, threshold=2)
    >>> interpolate([r, s]) # Two shares (at threshold).
    123
    >>> interpolate([s, t]) # Two shares (at threshold).
    123
    >>> interpolate([r, t]) # Two shares (at threshold).
    123

    If the ``compact`` argument is ``True``, the modulus is not included in the
    shares. This makes it possible to avoid storing a copy of the modulus in
    every share (*e.g.*, to reduce memory usage).

    >>> shares(17, 2, modulus=41, compact=True)[0].modulus
    Traceback (most recent call last):
      ...
    AttributeError: 'share' object has no attribute 'modulus'

    Attempts to invoke this function on a plaintext that is greater than the
    supplied prime modulus raise an exception.

    >>> shares(256, 3, modulus=31)
    Traceback (most recent call last):
      ...
    ValueError: plaintext must be a nonnegative integer strictly less than the prime modulus

    Other invocations with invalid parameter values also raise exceptions.

    >>> shares('abc', 3, 17)
    Traceback (most recent call last):
      ...
    TypeError: plaintext must be an integer
    >>> shares(1, 'abc', 17)
    Traceback (most recent call last):
      ...
    TypeError: quantity of shares must be an integer
    >>> shares(1, 3, 'abc')
    Traceback (most recent call last):
      ...
    TypeError: prime modulus must be an integer
    >>> shares(1, 3, 7, 'abc')
    Traceback (most recent call last):
      ...
    TypeError: threshold must be an integer
    >>> shares(1, 3, 7, compact='abc')
    Traceback (most recent call last):
      ...
    TypeError: compactness argument must be a boolean
    >>> shares(-2, 3, 17)
    Traceback (most recent call last):
      ...
    ValueError: plaintext must be a nonnegative integer
    >>> shares(1, 1, 17)
    Traceback (most recent call last):
      ...
    ValueError: quantity of shares must be at least 2
    >>> shares(1, 2**32, 17)
    Traceback (most recent call last):
      ...
    ValueError: quantity of shares must be strictly less than the modulus
    >>> shares(1, 2**32, (2**127) - 1)
    Traceback (most recent call last):
      ...
    ValueError: quantity of shares must be an integer that can be represented using at most 32 bits
    >>> shares(1, 3, 1)
    Traceback (most recent call last):
      ...
    ValueError: prime modulus must be at least 2

    Requesting fewer shares than needed to reconstruct is not permitted.

    >>> shares(1, quantity=3, modulus=11, threshold=7)
    Traceback (most recent call last):
      ...
    ValueError: threshold must be a positive integer less than the quantity of shares

    Requesting a larger set of shares than is necessary to reconstruct the
    original plaintext is permitted.

    >>> len(shares(1, quantity=7, modulus=11, threshold=3))
    7
    """
    # pylint: disable=too-many-branches
    if not isinstance(plaintext, int):
        raise TypeError('plaintext must be an integer')

    if not isinstance(quantity, int):
        raise TypeError('quantity of shares must be an integer')

    if not isinstance(modulus, int):
        raise TypeError('prime modulus must be an integer')

    if threshold is not None and not isinstance(threshold, int):
        raise TypeError('threshold must be an integer')

    if not isinstance(compact, bool):
        raise TypeError('compactness argument must be a boolean')

    if plaintext < 0:
        raise ValueError('plaintext must be a nonnegative integer')

    if modulus < 2:
        raise ValueError('prime modulus must be at least 2')

    if plaintext < 0 or plaintext >= modulus:
        raise ValueError(
            'plaintext must be a nonnegative integer strictly less ' +
            'than the prime modulus'
    )

    if quantity < 2:
        raise ValueError('quantity of shares must be at least 2')

    if quantity > modulus - 1:
        raise ValueError(
            'quantity of shares must be strictly less than the modulus'
        )

    if quantity >= 2 ** 32:
        raise ValueError(
            'quantity of shares must be an integer that can be represented ' +
            'using at most 32 bits'
        )

    # Use the maximum threshold if one is not specified.
    threshold = threshold or quantity
    if threshold < 1 or threshold > quantity:
        raise ValueError(
            'threshold must be a positive integer less than the quantity of shares'
        )

    # Create the coefficients.
    coefficients = (
        [plaintext] +
        [secrets.randbelow(modulus) for _ in range(1, threshold)]
    )

    # Compute each share value such that ``values[i] = f(i)`` if the polynomial
    # is ``f``.
    values = []
    for i in range(1, quantity + 1):
        value = 0
        for coefficient in reversed(coefficients):
            value *= i
            value += coefficient
            value %= modulus
        values.append(value)

    # Include index and (unless specified otherwise) modulus in share objects.
    return [
        share(index + 1, value, *([] if compact else [modulus]))
        for (index, value) in enumerate(values)
    ]

def add(
        *arguments: Union[share, Iterable[share]],
        modulus: Optional[int] = None,
        compact: bool = None
    ) -> Sequence[share]:
    """
    Perform addition of the supplied secret share objects (across all indices
    found within the provided shares).

    :param arguments: Share objects or iterables of share objects.
    :param modulus: Modulus to use when performing addition.
    :param compact: Flag to indicate that the modulus should not be included
        in the returned share objects.

    As share addition is generally straightforward (and more efficient) to
    perform without invoking a separate function (and all shares should not
    usually be available to a single party), this function is primarily made
    available to faciliate succinct testing. Thus, each argument can be either
    an individual share or an iterable of shares.

    >>> ss = shares(123, 3, modulus=1009)
    >>> ts = shares(456, 3, modulus=1009)
    >>> interpolate(add(ss, ts))
    579
    >>> interpolate(add([*ss, *ts]))
    579
    >>> ss = shares(123, 3, modulus=1009, compact=True)
    >>> ts = shares(456, 3, modulus=1009, compact=True)
    >>> interpolate(add([*ss, *ts], modulus=1009, compact=True), modulus=1009)
    579

    This function adds share values across all indices found in the :obj:`share`
    objects provided across all arguments. Thus, the particular grouping and
    order of shares is not consequential.

    >>> ss = shares(123, 3, modulus=1009)
    >>> ts = shares(456, 3, modulus=1009)
    >>> interpolate(add(ss + ts))
    579
    >>> interpolate(add(ss, ts))
    579
    >>> interpolate(add(reversed(ss + ts)))
    579
    >>> interpolate(add(list(reversed(ss)) + list(reversed(ts))))
    579

    However, for convenience within scenarios involving only a single index
    (such as when using this function to add shares that do not contain a
    modulus component because :obj:`~shamirs.shamirs.share.__add__` cannot do
    so), a single share is returned if all supplied arguments are individual
    shares.

    >>> add(share(2, 123, 1009), share(2, 456, 1009))
    share(2, 579, 1009)

    Similarly, the returned shares do not contain a modulus component if all
    shares in the arguments also do not contain a modulus component (although
    an explicit ``compact`` argument value takes precedence over this).

    >>> add(share(2, 123), share(2, 456), modulus=1009)
    share(2, 579)
    >>> add(share(2, 123, 1009), share(2, 456, 1009), compact=True)
    share(2, 579)
    >>> add(share(2, 123), share(2, 456), modulus=1009, compact=True)
    share(2, 579)
    >>> add(share(2, 123), share(2, 456), modulus=1009, compact=False)
    share(2, 579, 1009)

    Invocations with invalid parameter values raise exceptions.

    >>> add([], 123)
    Traceback (most recent call last):
      ...
    TypeError: arguments must be share objects or iterables of share objects
    >>> add(modulus=123)
    Traceback (most recent call last):
      ...
    TypeError: arguments must contain at least one share object
    >>> add([share(2, 123, 1009)], 'abc')
    Traceback (most recent call last):
      ...
    TypeError: arguments must be share objects or iterables of share objects
    >>> add([*ss, *ts], modulus='abc')
    Traceback (most recent call last):
      ...
    TypeError: modulus must be an integer
    >>> add(shares(123, 3, 1223) + shares(123, 3, 1021))
    Traceback (most recent call last):
      ...
    ValueError: all share objects must have the same modulus or no modulus
    >>> add(shares(123, 3, 1223) + shares(123, 3, 1223), modulus=1021)
    Traceback (most recent call last):
      ...
    ValueError: modulus in share objects does not match modulus argument
    >>> add(shares(123, 3, 1223) + shares(123, 3, 1223), compact='abc')
    Traceback (most recent call last):
      ...
    TypeError: compactness argument must be a boolean
    >>> add(shares(123, 3, 1223, compact=True) + shares(123, 3, 1223, compact=True))
    Traceback (most recent call last):
      ...
    ValueError: modulus is not found in share objects and is not provided as an argument
    """
    # pylint: disable=too-many-branches
    message = 'arguments must be share objects or iterables of share objects'
    iterables = False # Return output as a single share object by default.
    inputs = [] # Store shares for reuse, even if iterables are supplied.
    for argument in arguments:
        if isinstance(argument, share):
            inputs.append(argument)
        elif isinstance(argument, Iterable):
            iterables = True # Return even a single-share output as a sequence.
            for item in argument:
                if not isinstance(item, share):
                    raise TypeError(message)
                inputs.append(item)
        else:
            raise TypeError(message)

    if len(inputs) == 0:
        raise TypeError('arguments must contain at least one share object')

    if modulus is not None and not isinstance(modulus, int):
        raise TypeError('modulus must be an integer')

    moduli = list({share_.modulus if len(share_) == 3 else None for share_ in inputs})
    if len(moduli) > 1:
        raise ValueError('all share objects must have the same modulus or no modulus')

    if modulus is not None and moduli[0] is not None and modulus != moduli[0]:
        raise ValueError(
            'modulus in share objects does not match modulus argument'
        )

    if modulus is None and moduli[0] is None:
        raise ValueError(
            'modulus is not found in share objects and is not provided as an argument'
        )

    modulus = modulus or moduli[0]

    if compact is not None and not isinstance(compact, bool):
        raise TypeError('compactness argument must be a boolean')

    index_to_value = {share_.index: 0 for share_ in inputs}
    for share_ in inputs:
        index_to_value[share_.index] += share_.value
        index_to_value[share_.index] %= modulus

    outputs = [
        share(
            *item,
            *( # Exclude modulus if so instructed or if arguments had no modulus.
                []
                if compact is True or (compact is None and moduli[0] is None) else
                [modulus]
            )
        )
        for item in index_to_value.items()
    ]

    # Return one share object if the arguments were all individual share objects.
    return outputs[0] if len(outputs) == 1 and not iterables else outputs

def mul(
        argument: Union[share, Iterable[share]],
        scalar: int,
        modulus: Optional[int] = None,
        compact: bool = None
    ) -> Union[share, Sequence[share]]:
    """
    Perform scalar multiplication of each secret share object in the supplied
    iterable of secret share objects.

    :param argument: Share object or iterable of share objects.
    :param scalar: Integer scalar by which to multiply the share objects.
    :param modulus: Modulus to use when performing scalar multiplication.
    :param compact: Flag to indicate that the modulus should not be included
        in the returned share objects.

    As scalar multiplication is generally straightforward (and more) efficient
    to perform without invoking a separate method (and all shares should not
    usually be available to a single party), this method is primarily made
    available to faciliate succinct testing.

    >>> shares_ = shares(123, 3, modulus=1009)
    >>> interpolate(mul(shares_, scalar=3, modulus=1009), modulus=1009)
    369

    This function can operate on both individual shares and on iterables
    thereof. However, for convenience within scenarios involving only a single
    share (such as when using this function to multiply a share that does not
    contain a modulus component because :obj:`~shamirs.shamirs.share.__mul__`
    cannot do so), a single share is returned.

    >>> mul(share(1, 123, 1009), scalar=2)
    share(1, 246, 1009)
    >>> mul(share(1, 123), scalar=2, modulus=1009)
    share(1, 246)

    Similarly, the returned shares do not contain a modulus component if all
    shares in the arguments also do not contain a modulus component (although
    an explicit ``compact`` argument value takes precedence over this).

    >>> mul([share(1, 123), share(2, 234)], scalar=3, modulus=1009)
    [share(1, 369), share(2, 702)]
    >>> mul([share(1, 123, 1009), share(2, 234, 1009)], scalar=3, compact=True)
    [share(1, 369), share(2, 702)]
    >>> mul([share(1, 123), share(2, 234)], scalar=3, modulus=1009, compact=True)
    [share(1, 369), share(2, 702)]
    >>> mul([share(1, 123), share(2, 234)], scalar=3, modulus=1009, compact=False)
    [share(1, 369, 1009), share(2, 702, 1009)]

    Invocations with invalid parameter values raise exceptions.

    >>> mul(False, 123)
    Traceback (most recent call last):
      ...
    TypeError: argument must be share object or iterable of share objects
    >>> mul([], 123)
    Traceback (most recent call last):
      ...
    TypeError: iterable must contain one or more share objects
    >>> mul(shares_, 'abc')
    Traceback (most recent call last):
      ...
    TypeError: scalar must be an integer
    >>> mul(shares_, 123, 'abc')
    Traceback (most recent call last):
      ...
    TypeError: modulus must be an integer
    >>> mul(shares(123, 3, 1223) + shares(123, 3, 1021), 123)
    Traceback (most recent call last):
      ...
    ValueError: all share objects must have the same modulus
    >>> mul(shares(123, 3, 1223), 123, 1021)
    Traceback (most recent call last):
      ...
    ValueError: modulus in share objects does not match modulus argument
    >>> mul(shares(123, 3, modulus=1009), 123, compact='abc')
    Traceback (most recent call last):
      ...
    TypeError: compactness argument must be a boolean
    >>> mul(shares(123, 3, modulus=1009, compact=True), 123)
    Traceback (most recent call last):
      ...
    ValueError: modulus is not found in share objects and is not provided as an argument
    """
    if (not isinstance(argument, share)) and (not isinstance(argument, Iterable)):
        raise TypeError(
            'argument must be share object or iterable of share objects'
        )

    iterable = False # Return output as a single share object by default.
    inputs = None
    if isinstance(argument, share):
        inputs = [argument]
    else:
        iterable = True # Return even a single-share output as a sequence.
        inputs = list(argument) # Save iterable of items in argument for reuse.
        if len(inputs) == 0 or not all (isinstance(item, share) for item in inputs):
            raise TypeError('iterable must contain one or more share objects')

    if not isinstance(scalar, int):
        raise TypeError('scalar must be an integer')

    if modulus is not None and not isinstance(modulus, int):
        raise TypeError('modulus must be an integer')

    moduli = list({share_.modulus if len(share_) == 3 else None for share_ in inputs})
    if len(moduli) > 1:
        raise ValueError('all share objects must have the same modulus')

    if modulus is not None and moduli[0] is not None and modulus != moduli[0]:
        raise ValueError(
            'modulus in share objects does not match modulus argument'
        )

    if modulus is None and moduli[0] is None:
        raise ValueError(
            'modulus is not found in share objects and is not provided as an argument'
        )

    modulus = modulus or moduli[0]

    if compact is not None and not isinstance(compact, bool):
        raise TypeError('compactness argument must be a boolean')

    outputs = [
        share(
            share_.index,
            (share_.value * scalar) % modulus,
            *( # Exclude modulus if so instructed or if arguments had no modulus.
                []
                if compact is True or (compact is None and moduli[0] is None) else
                [modulus]
            )
        )
        for share_ in inputs
    ]

    # Return one share object if the argument was a single share object.
    return outputs[0] if len(outputs) == 1 and not iterable else outputs

def interpolate(
        shares: Iterable[share], # pylint: disable=redefined-outer-name
        modulus: Optional[int] = None,
        threshold: Optional[int] = None
    ) -> int:
    """
    Calculate an integer plaintext from a sequence of secret shares using
    Lagrange interpolation (via the :obj:`~lagrange.lagrange.interpolate` function
    exported by the `lagrange <https://pypi.org/project/lagrange>`__ library).

    :param shares: Iterable of secret shares from which to reconstruct a plaintext.
    :param modulus: Modulus to use when performing interpolation.
    :param threshold: Minimum number of shares that are required to reconstruct
        a plaintext.

    The appropriate order for the shares is already encoded in the individual
    :obj:`share` objects (assuming they were created using the :obj:`shares`
    function). Thus, they can be supplied in any order.

    >>> interpolate(shares(5, 3, modulus=31))
    5
    >>> interpolate(shares(123, 12))
    123
    >>> interpolate(reversed(shares(123, 12)))
    123

    In the example below, the plaintext ``123`` was shared with twenty parties 
    such that at least twelve must collaborate to reconstruct theplaintext.

    >>> interpolate(shares(123, 20, 1223, 12)[:12], threshold=12) # First twelve shares.
    123
    >>> interpolate(shares(123, 20, 1223, 12)[20-12:], threshold=12) # Last twelve shares.
    123
    >>> interpolate(shares(123, 20, 1223, 12)[:15], threshold=12) # First fifteen shares.
    123
    >>> interpolate(shares(123, 20, 1223, 12)[:11], threshold=12) # Only eleven shares.
    Traceback (most recent call last):
      ...
    ValueError: not enough points for a unique interpolation

    If the threshold is known to be different than the number of shares,
    it can be specified as such to improve performance.

    >>> ss = shares(123, 256, threshold=2)
    >>> interpolate(ss) # Slower.
    123
    >>> interpolate(ss, threshold=2) # Faster.
    123

    Any attempt to interpolate using a threshold value that is smaller than the
    threshold value originally specified when the shares were created yields an
    arbitrary output. However, no confirmation is performed (at the time of
    interpolation) that interpolation is being performed with the correct
    threshold value.

    >>> 123 != interpolate(shares(123, 20, (2**31) - 1, 12)[:11], threshold=11)
    True
    >>> 123 != interpolate(shares(123, 20, (2**31) - 1, 2)[:1], threshold=1)
    True

    Any attempt to interpolate using a threshold value that is larger than the
    threshold value originally specified when the shares were created returns
    the original secret-shared plaintext.

    >>> interpolate(shares(123, 20, (2**31) - 1, 12)[:13], threshold=13)
    123

    Invocations with invalid parameter values raise exceptions.

    >>> interpolate([1, 2, 3])
    Traceback (most recent call last):
      ...
    TypeError: iterable must contain one or more share objects
    >>> interpolate(shares(123, 3, 1223) + shares(123, 3, 1021))
    Traceback (most recent call last):
      ...
    ValueError: all share objects must have the same modulus
    >>> interpolate(shares(123, 3, 1021) + shares(123, 3, 1021), modulus=1009)
    Traceback (most recent call last):
      ...
    ValueError: modulus in share objects does not match modulus argument
    >>> interpolate([share(1, 5), share(2, 7)])
    Traceback (most recent call last):
      ...
    ValueError: modulus is not found in share objects and is not provided as an argument
    >>> interpolate(shares(5, 3, modulus=31), threshold='abc')
    Traceback (most recent call last):
      ...
    TypeError: threshold must be an integer
    """
    shares = list(shares) # Store shares for reuse, even if an iterable is supplied.

    if len(shares) == 0 or not all (isinstance(share_, share) for share_ in shares):
        raise TypeError('iterable must contain one or more share objects')

    moduli = list({share.modulus if len(share) == 3 else None for share in shares})
    if len(moduli) > 1:
        raise ValueError('all share objects must have the same modulus')

    if modulus is not None and moduli[0] is not None and modulus != moduli[0]:
        raise ValueError(
            'modulus in share objects does not match modulus argument'
        )

    if modulus is None and moduli[0] is None:
        raise ValueError(
            'modulus is not found in share objects and is not provided as an argument'
        )

    if threshold is not None and not isinstance(threshold, int):
        raise TypeError('threshold must be an integer')

    return lagrange.interpolate(
        [(share_.index, share_.value) for share_ in shares],
        modulus or moduli[0],
        (threshold or len(shares)) - 1
    )

reconstruct: Callable[[Iterable[share], Optional[int], Optional[int]], int] = interpolate
"""
Alias for :obj:`interpolate`.

>>> reconstruct(shares(5, 3, modulus=31))
5
"""

recover: Callable[[Iterable[share], Optional[int], Optional[int]], int] = interpolate
"""
Alias for :obj:`interpolate`.

>>> recover(shares(5, 3, modulus=31))
5
"""

reveal: Callable[[Iterable[share], Optional[int], Optional[int]], int] = interpolate
"""
Alias for :obj:`interpolate`.

>>> reveal(shares(5, 3, modulus=31))
5
"""

if __name__ == '__main__': # pragma: no cover
    doctest.testmod()
