# from lcapy import Circuit

# # Load the netlist file directly
# cct = Circuit("C:\\Users\\Saketh Akella\\Downloads\\demo1.net")

# # Render and save the schematic picture
# cct.draw('output_schematic.png')
import os
from pathlib import Path
import subprocess
from PyLTSpice import RawRead
from matplotlib import pyplot as plt

LTR = RawRead("C:\\Users\\Saketh Akella\\Downloads\\demo1.raw")

print(LTR.get_trace_names())
