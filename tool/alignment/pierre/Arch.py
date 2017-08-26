# This is just emulating a C-style enum

import sys
import traceback
from Globals import er

class Arch():
	X86 = 0
	ARM = 1
	POWER = 2

	@classmethod
	def sanityCheck(cls, val):
		if val != cls.X86 and val != cls.ARM and val != cls.POWER:
			er("bad value for Arch enum: " + str(val) + "\n")
			for line in traceback.format_stack():
				print line.strip()
			sys.exit(-1)
