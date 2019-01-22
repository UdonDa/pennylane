# Copyright 2018 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Utilities
=========

**Module name:** :mod:`pennylane.utils`

.. currentmodule:: pennylane.utils

This module contains utilities and auxiliary functions, which are shared
across the PennyLane submodules.

.. raw:: html

    <h3>Summary</h3>

.. autosummary::
    _flatten
    _unflatten
    unflatten

.. raw:: html

    <h3>Code details</h3>
"""
import collections
import numbers

import autograd.numpy as np

from .variable  import Variable


def _flatten(x):
    """Iterate through an arbitrarily nested structure, flattening it in depth-first order.

    See also :func:`_unflatten`.

    Args:
        x (array, Iterable, other): each element of the Iterable may itself be an iterable object

    Yields:
        other: elements of x in depth-first order
    """
    if isinstance(x, np.ndarray):
        yield from _flatten(x.flat)  # should we allow object arrays? or just "yield from x.flat"?
    elif isinstance(x, collections.Iterable) and not isinstance(x, (str, bytes)):
        for item in x:
            yield from _flatten(item)
    else:
        yield x


def _unflatten(flat, model):
    """Restores an arbitrary nested structure from a flattened iterable.

    See also :func:`_flatten`.

    Args:
        flat (array): 1D array of items
        model (array, Iterable, Number): model nested structure

    Returns:
        (other, array): first elements of flat arranged into the nested
        structure of model, unused elements of flat
    """
    if isinstance(model, (numbers.Number, Variable)) and not isinstance(model, collections.Iterable):
        return flat[0], flat[1:]
    elif isinstance(model, collections.Iterable):
        if isinstance(model, np.ndarray):
            l = model.shape[0] if model.shape != () else 0
        else:
            l = len(model)
        if l == 0: #l=0 can only happen for single element np.arrays such as np.array(4) and for empty tuples
            if isinstance(model, np.ndarray):
                return np.array(flat[0], dtype=model.dtype), flat[1:]
            else:
                return (), flat

        # Now we know that model is not just iterable, but has length at least 1 and can actually be indexed.

        if isinstance(model, np.ndarray):
            # For np.arrays there is a special shortcut if they are not yagged
            size = model.size
            #if size == np.prod(model.shape) and np.all([isinstance(x, np.ndarray) and x.shape == model[0].shape for x in model]): # I suppose, ultimately, the unflattening via reshaping should be done conditional on this but for testing I do it always
            #return np.array(flat)[:size].reshape(model.shape), flat[size:] # with this line commented out, many of the existing tests fail, but with it commented in, many of the tests in test_utils.py fails. Somehow, it appears, during this reshaping process, Variables are replaced by their parameter values. I can see that, because with this line enabled, my unflatten() sometimes returns np.arrays of floats or ints, whereas if I treat the same combination of flat and model without this line as an iterable, then this function is returning np.arrays of Variables!


        # As we have to unflatten depth-first, we need to keep track of the "tail"
        # of not yet used elements but also want to yield from recursive calls of
        # _unflatten(). The cleanest way to do this is via a class that keeps track
        # of the "global" state of the tail while yielding and also decides what
        # the resulting dtype should be:
        class Unflattener:
            def __init__(self, flat, model):
                self.flat = flat
                self.model = model
                self.encountered_variable = False

            def gen(self):
                for i, x in enumerate(model):
                    res, self.flat = _unflatten(self.flat, x)
                    if isinstance(res, Variable):
                        self.encountered_variable = True
                    yield res

            def tail(self):
                return self.flat

            def dtype(self):
                if self.encountered_variable:
                    return object
                else:
                    return self.model.dtype

        unflattener = Unflattener(flat, model)

        if isinstance(model, np.ndarray):
            # the following two lines should be equivalent, but the latter leads to errors sometimes
            return np.array(list(unflattener.gen()), dtype=unflattener.dtype()), unflattener.tail()
            #return np.fromiter(unflattener.gen(), dtype=unflattener.dtype()), unflattener.tail()
        else:
            return (type(model))(unflattener.gen()), unflattener.tail()
    else:
        raise TypeError('Unsupported type in the model: {}'.format(type(model)))


def unflatten(flat, model):
    """Wrapper for :func:`_unflatten`.
    """
    # pylint:disable=len-as-condition
    res, tail = _unflatten(np.asarray(flat), model)

    print("unflatten called with\n model="+str(model)+"\n  flat="+str(flat)+"\nreturn="+str(res)+"\n")
    if len(tail) != 0:
        raise ValueError('Flattened iterable has more elements than the model.')
    return res
