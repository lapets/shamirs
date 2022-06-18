"""
Minimal pure-Python implementation of Shamir's Secret Sharing scheme.
"""
import doctest
from secrets import token_bytes
from lagrange import interpolate

def _randint(bound):
    """
    Generate a random integer according to an approximately uniform distribution
    via rejection sampling.
    """
    length = 1 + (bound.bit_length() // 8)
    value = int.from_bytes(token_bytes(length), 'little')
    while value >= bound:
        value = int.from_bytes(token_bytes(length), 'little')
    return value

def share(value, parties, prime, coefficients = None):
    """
    Transforms an integer into a number of shares given a prime modulus and a
    number of parties.

    >>> len(share(1, 3, 31))
    3
    >>> len(share(123, 10, 41))
    10
    """
    shares = {}
    threshold = parties - 1

    # Use random polynomial coefficients if none were supplied.
    if coefficients is None:
        coefficients = [_randint(prime - 1) for _ in range(1, threshold)]

    # Add the base coefficient.
    coefficients = [value] + coefficients

    # Compute each share such that shares[i] = f(i).
    for i in range(1, parties+1):
        shares[i] = coefficients[0]
        for j in range(1, len(coefficients)):
            shares[i] = (shares[i] + coefficients[j] * pow(i, j)) % prime

    return shares

def build(shares, prime):
    """
    Reassemble an integer value from a collection of secret shares.

    >>> build(share(5, 3, 31), 31)
    5
    >>> build(share(123, 12, 15485867), 15485867)
    123
    """
    return interpolate(shares, prime)

if __name__ == "__main__": # pragma: no cover
    doctest.testmod()
