import X86, Arm, Power
import argparse
import os, sys, shutil
from Arch import Arch
import Linker
import Globals
import glob
from Globals import er

# Instantiate one object representing each architecture and put them
# in a dictionary indexed by the Arch "enum" (see Arch.py)
x86_obj = X86.X86()
arm_obj = Arm.Arm()
power_obj = Power.Power()

archs = { 	Arch.X86 : x86_obj,
			Arch.ARM : arm_obj,
			Arch.POWER : power_obj,
		}

#TODO add power later
considered_archs = [archs[Arch.X86], archs[Arch.ARM]]
considered_sections = [".text", ".data", ".bss", ".rodata", ".tdata", 
		".tbss"]

###############################################################################
# buildArgparser
###############################################################################
def buildArgParser():
	""" Construct the command line argument parser object """

	res = argparse.ArgumentParser(description="Align symbols in binaries from" +
		" multiple ISAs")
	
	res.add_argument("--x86-bin", help="Path to the input x86 executable",
		required=True)
	res.add_argument("--arm-bin", help="Path to the input ARM executable",
		required=True)
	res.add_argument("--x86-map", help="Path to the x86 memory map file " +
		"corresponding to the x86 binary (generated through ld -MAP)",
		required=True)
	res.add_argument("--arm-map", help="Path to the ARM memory map file " +
		"corresponding to the x86 binary (generated through ld -MAP)",
		required=True)
	res.add_argument("--x86-object-files", nargs="+", help="List of input " +
		"object files (x86)", required=True)
	res.add_argument("--arm-object-files", nargs="+", help="List of input " +
		"object files (arm)", required=True)
	res.add_argument("--power-object-files", nargs="+", help="List of input " +
	"object files (power)", required=False) #TODO set to true later
	res.add_argument("--work-dir", help="Temporary work directory",
		default="/tmp/align")
	res.add_argument("--clean-work-dir", type=bool, 
		help="Delete work directory when done",	default=True)

	return res

###############################################################################
# parseAndCheckArgs
###############################################################################
def parseAndCheckArgs(parser):
	args = parser.parse_args()
	# TODO checks here

	return args

###############################################################################
# prepareWorkDir
###############################################################################
def prepareWorkDir(args):
	""" Clean the working directory and copy input files in it """
	workdir = args.work_dir
	if os.path.exists(workdir):
		if not os.path.isdir(workdir):
			er(workdir + " exists and is not a directory, remove it first")
			sys.exit(-1)
		shutil.rmtree(workdir)

	os.makedirs(workdir)
	
	# Copy binaries and map files
	# TODO power
	shutil.copy(args.x86_bin, workdir + "/" + 
		archs[Arch.X86].getExecutable())
	shutil.copy(args.arm_bin, workdir + "/" + 
		archs[Arch.ARM].getExecutable())
	shutil.copy(args.x86_map, workdir + "/" + 
		archs[Arch.X86].getMapFile())
	shutil.copy(args.arm_map, workdir + "/" + 
		archs[Arch.ARM].getMapFile())

	# Copy linker script templates
	# TODO power
	templates_loc = Globals.POPCORN_LOCATION + "/share/align-script-templates"
	linkerScriptTemplates=os.listdir(templates_loc)
	for f in linkerScriptTemplates:
		shutil.copy(templates_loc + "/" + f, workdir + "/" + f)

	# Copy object files
	# TODO power
	x86ObjsSubdir = Globals.X86_OBJS_SUBDIR
	armObjsSubdir = Globals.ARM_OBJS_SUBDIR
	os.makedirs(workdir + "/" + x86ObjsSubdir)
	os.makedirs(workdir + "/" + armObjsSubdir)
	for f in args.x86_object_files:
		shutil.copy(f, workdir + "/" + x86ObjsSubdir + "/" + 
			os.path.basename(f))
	for f in args.arm_object_files:
		shutil.copy(f, workdir + "/" + armObjsSubdir + "/" + 
			os.path.basename(f))

	return

###############################################################################
# setObjectFiles
###############################################################################
def setObjectFiles(args):
	workdir = args.work_dir
	
	archs[Arch.X86].setObjectFiles(glob.glob(workdir + "/" + 
		Globals.X86_OBJS_SUBDIR + "/*.o"))
	archs[Arch.ARM].setObjectFiles(glob.glob(workdir + "/" + 
		Globals.ARM_OBJS_SUBDIR + "/*.o"))
	# TODO power

###############################################################################
# Order symbols
###############################################################################
# in each section, the symbols will be ordered by number of architectures 
# referencing the symbols in questions
# sl is a list of Symbol instances (should correspond to one section)
# return as a result an ordered symbol list
def orderSymbolList(sl):
	res = []
	tmp_res = [] #TODO remove

	# TODO Explain the trick
	for order in list(reversed(range(1, len(considered_archs)+1))):
		for symbol in sl:
			# TODO remove this shit
			if symbol.getName() == ".text" or symbol.getName() == ".text.dummy":
				tmp_res.append(symbol)
				continue
			# TODO end remove this shit
			referencingArchs = len(considered_archs)
			for arch_instance in considered_archs:
				arch = arch_instance.getArch()
				if symbol.getAddress(arch) == -1:  # not referenced by this arch
					referencingArchs -= 1

			if referencingArchs == order:
				res.append(symbol)

	# TODO remove
	res = res + tmp_res

	return res

###############################################################################
# align
##############################################################################
# sl is a list of symbols (same as for orderSymbolsList that should correspond
# to one section
# here is what we do:
#
#     Arch A            Arch B              Arch C               Arch D
#                                                         (symbol not present)
# +--------------+  +---------------+  +----------------+  +---------------+
# |  Pad before  |  | Pad before    |  | Pad before     |  |  Pad before   |
# +--------------+  +---------------+  +----------------+  +---------------+
# +--------------+  +---------------+  +----------------+  +---------------+
# |   Symbol     |  |               |  |     Symbol     |  |               |
# |              |  |               |  |                |  |               |
# |              |  |   Symbol      |  +----------------+  |               |
# +--------------+  |               |  +----------------+  | pad after     |
# +--------------+  |               |  |                |  |               |
# | Pad after    |  |               |  |  pad after     |  |               |
# |              |  |               |  |                |  |               |
# |              |  |               |  |                |  |               |
# +--------------+  +---------------+  +----------------+  +---------------+
#
# "pad before" automatically added by the linker to satisfy the alignment 
# constraint we put on the symobl (we choose the largest alignment constaint of 
# all referencing architectures. We need to add it by hand on each architecture
# that is not referencing the symbol, though. 
# "pad after" is added by us so that the next symbol to be processed starts at 
# the same address on each architecture
# 
# TODO ths for now assumes there is no duplicate symbols which is not the case
def align(sl):
	address = 0
	
	for symbol in sl:
		padBefore = 0  # padding we'll need to add before that symbol
		# set the alignment for all referencing arch to the largest one
		alignment = symbol.setLargestAlignment()
		while ((address + padBefore) % alignment) != 0:
			padBefore += 1

		# Add padding "before" for architectures not referencing the symbol
		for arch in symbol.getArchitecturesNotReferencing():
			symbol.incrPaddingBefore(padBefore, arch)

		# Now get the largest symbol size among archs to compute paddign to put
		# after the symbol on
		largestSize = symbol.getLargetSizeVal()

		# Add some padding to referencing archs for which the size is smaller
		# than the largest one
		for arch in symbol.getArchitecturesReferencing():
			padAfter = largestSize - symbol.getSize(arch)
			symbol.incrPaddingAfter(padAfter, arch)

		# For the architecture not referencing the symbol, we should add padding 
		# equals to the largest size
		for arch in symbol.getArchitecturesNotReferencing():
			symbol.incrPaddingAfter(largestSize, arch)

		# increment our "iterator" so we can compute the padding "before" to
		# add on the next symbol to process
		address += padBefore + largestSize

	return sl


###############################################################################
# main
###############################################################################
if __name__ == "__main__":
	# Argument parsing stuff
	parser = buildArgParser()
	args = parseAndCheckArgs(parser)

	# Prepare work directory and switch to it as cwd
	prepareWorkDir(args)
	os.chdir(args.work_dir)
	setObjectFiles(args)

	# List of per-section symbols that we are going to fill and manipulate
	work = {}
	for section in considered_sections:
		work[section] = []

	# Add symbols to the list
	for arch in considered_archs:
		arch.updateSymbolsList(work)

	# Order symbols in each section based on the number of arch referencing 
	# each symbol 
	for section in considered_sections:
		work[section] = orderSymbolList(work[section])

	# perform the alignment
	for section in considered_sections:
		work[section] = align(work[section])

	# write linker script then link
	for arch in considered_archs:
		Linker.Linker.produceLinkerScript(work, arch)
		arch.goldLink(arch.getObjectFiles())	
