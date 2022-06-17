"""
Python library with a minimal native implementation of Shamir's Secret
Sharing algorithm.
"""
import doctest
from random import randint
from lagrange import interpolate

def share(value, parties, prime, coefficients = None):
    """
    Turns an integer into a number of shares given a modulus and a
    number of parties.
    """
    shares = {}
    threshold = parties - 1

    # Use random polynomial coefficients if none were supplied.
    if coefficients is None:
        coefficients = [randint(0, prime - 1) for _ in range(1, threshold)]

    # Add the base coefficient.
    coefficients = [value] + coefficients

    # Compute each share such that shares[i] = f(i).
    for i in range(1, parties+1):
        shares[i] = coefficients[0]
        for j in range(1, len(coefficients)):
            shares[i] = (shares[i] + coefficients[j] * pow(i,j)) % prime

    return shares

def build(shares, prime):
    """
    Turns a list of shares back into the corresponding value.

    >>> build(share(5, 3, 17), 17)
    5
    >>> build(share(123, 12, 15485867), 15485867)
    123
    """
    return interpolate(shares, prime)

if __name__ == "__main__": # pragma: no cover
    doctest.testmod()
