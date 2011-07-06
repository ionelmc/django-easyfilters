

def auto_ranges(lower, upper, max_items):
    # TODO - round to produce nice looking ranges.
    step = (upper - lower)/max_items
    ranges = [(lower + step * i, lower + step * (i+1)) for i in xrange(max_items)]
    return ranges
