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
    if coefficients is None:
        # Random polynomial coefficients.
        polynomial = [value] + [randint(0,prime-1) for _ in range(1,threshold)]
    else:
        polynomial = [value] + coefficients

    # Compute each share such that shares[i] = f(i).
    for i in range(1, parties+1):
        shares[i] = polynomial[0]
        for j in range(1, len(polynomial)):
            shares[i] = (shares[i] + polynomial[j] * pow(i,j)) % prime

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

if __name__ == "__main__":
    doctest.testmod()
