# -*- coding: utf-8 -*-
"""
This program draws a heart using MatPlotLib.

You don't have to worry about how it does it, just
make sure that it runs. If it's successful, a heart
will appear in a new window.

I need my PyCharm, habits are hard to break lol

If I'm actually not allowed to use PyCharm just give me a 0 and I'll resubmit it
I have it installed and ready I am just much more familiar with PyCharm
"""

# Import graphing library
import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox

# Import math library
from numpy import pi, sin, cos, arange

# Define some simple constants
CIRCLE_CIRCUMFERENCE = 2 * pi
STEP_RATE = 0.1

# Make a list of decimal numbers from 0 to 2*PI
steps = arange(0, CIRCLE_CIRCUMFERENCE, STEP_RATE)

# Calculate the X/Y coordinates using math
x_coordinates = (2 * sin(steps)) ** 3
y_coordinates = (13 * cos(1 * steps) - 5 * cos(2 * steps) -
                 2 * cos(3 * steps) - 1 * cos(4 * steps))

# Make the graph style XKCD
plt.xkcd()

# Plot the coordinates

plt.plot(x_coordinates, y_coordinates, color='red')

# Make the graph appear
plt.show()
