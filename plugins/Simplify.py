#Name: Simplify short moves
#Info: Reduces number of short moves; too many can cause stuttering
#Depend: GCode
#Type: postprocess
#Param: minSegment(float:0.1) Minimum segment length (mm)
#Param: minDeviation(float:0.02) Minimum allowed deviation from straight (mm)
#Param: verboseOut(bool:false) Verbose output

## Code originally by Johann C. Rocholl, adapted as plugin by Ryan D. Press

import math
import os
import re
import sys
print "simplifying..."

def should_skip(p0, p1, p2):
    """Check if p1 is on a straight line between p0 and p2."""
    if p0 is None:
        return False
    if p1 is None:
        return False
    if p2 is None:
        return False
    indices = range(len(p1))
    # Calculate vectors for p1 and p2 relative to p0.
    v1 = [p1[i] - p0[i] for i in indices]
    v2 = [p2[i] - p0[i] for i in indices]
    # Calculate the lengths of the relative vectors.
    l1 = math.sqrt(sum(v1[i] * v1[i] for i in indices))
    l2 = math.sqrt(sum(v2[i] * v2[i] for i in indices))
    if l2 < minSegment:
        # Ignore midpoint because the whole segment is very short.
        return 'length=%.5f (too short)' % l2
    ratio = l1 / l2  # Ratio of midpoint vs endpoint.
    # How far is the midpoint away from straight line?
    d = [v1[i] - v2[i] * ratio for i in indices]
    error = math.sqrt(sum(d[i] * d[i] for i in indices))
    if error > minDeviation:
        return False
    # Ignore midpoint because it is very close to the straight line.
    return 'ratio=%.5f error=%.5f (straight line)' % (ratio, error)


def rewrite(infile, outfile):
    p0 = None
    p1 = None
    previous = None
    for line in infile:
        match = re.match(r'^G1 X([-\d\.]+) Y([-\d\.]+) E([-\d\.]+)$',
                         line.rstrip())
        if match:
            p2 = [float(s) for s in match.groups()]
            message = should_skip(p0, p1, p2)
            if message:
                # Previous G1 is the midpoint of a straight line.
                stripped = previous.rstrip()
                newline = previous[len(stripped):]
                if verboseOut == True:
                    # Prefix with ; to ignore this line when printing.
                    previous = ';%s %s%s' % (stripped, message, newline)
                else:
                    previous = None
                p1 = p2
            else:
                p0 = p1
                p1 = p2
        else:
            p0 = None
            p1 = None
        if previous:
            outfile.write(previous)
        previous = line
    if previous:
        outfile.write(previous)


with open(filename, "r") as f:
    lines = f.readlines()

with open(filename, 'w') as f:
    rewrite(lines, f)

