from .mem_profile import display_top, MemProf, fmt_size
from .cpu_profile import CpuProfileContextManager

DEBUG_MEMORY = False
# only triggered by key press so can be on by default
DEBUG_CPU = True
