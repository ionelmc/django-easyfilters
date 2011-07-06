"""
Utilities to produce ranges of values for filters
"""

from decimal import Decimal, DecimalTuple, ROUND_HALF_EVEN, ROUND_DOWN, ROUND_UP
import math


def round_dec(d):
    return d._rescale(0, ROUND_HALF_EVEN)

def round_dec_down(d):
    return d._rescale(0, ROUND_DOWN)

def round_dec_up(d):
    return d._rescale(0, ROUND_UP)


def auto_ranges(lower, upper, max_items):
    if lower == upper:
        return [(lower, upper)]

    assert lower < upper

    input_type = type(lower)

    # Convert to decimals.
    lower_d = Decimal(lower)
    upper_d = Decimal(upper)

    step = (upper_d - lower_d)/max_items

    # For human presentable numbers, 'step' will preferable be something like 2,
    # 5, 10, or 0.1, 0.2, 0.5. etc.
    st = step.as_tuple()

    # It's not very helpful having exponent > 0, because these get displayed as
    # 1E+1 etc. But we also don't want things like 10.00000. So we make sure
    # we don't increase the exponent of step above zero

    exponent_offset = len(st.digits)
    if exponent_offset + st.exponent > 0:
        exponent_offset = -st.exponent
    zeros = [0] * (len(st.digits) - 1 - exponent_offset)

    candidate_steps = [Decimal(DecimalTuple(sign=st.sign,
                                            digits=[d] + zeros,
                                            exponent=st.exponent + exponent_offset))
                       for d in (1, 2, 5)]
    # Go one order bigger as well:
    candidate_steps.append(Decimal(DecimalTuple(sign=st.sign,
                                                digits=[1, 0] + zeros,
                                                exponent=st.exponent + exponent_offset)))

    for c_step in candidate_steps:
        # Use c_step to do rounding as well.
        lower_r = round_dec_down(lower_d / c_step) * c_step
        upper_r = round_dec_up(upper_d / c_step) * c_step
        num_steps = int(round_dec((upper_r - lower_r) / c_step))
        # If we are less than max_items, go with this.  (Note that smaller steps
        # are tried first).
        if num_steps <= max_items:
            ranges = []
            for i in xrange(num_steps):
                lower_i = input_type(lower_r + c_step * i)
                upper_i = input_type(lower_r + c_step * (i + 1))
                if i == num_steps - 1:
                    # make sure top item is rounded value
                    upper_i = input_type(upper_r)
                ranges.append((lower_i, upper_i))
            return ranges

    assert False, "Can't find a candidate set of ranges, logic error"
