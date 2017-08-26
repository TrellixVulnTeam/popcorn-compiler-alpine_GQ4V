from Arch import Arch

class Linker:

	_sectionmarker = {	".text" 	: "__TEXT__",
						".data" 	: "__DATA__",
						".bss"  	: "__BSS__",
						".rodata" 	: "__RODATA__",
						".tdata" 	: "__TDATA__",
						".tbss" 	: "__TBSS__" }

	@classmethod
	def getSectionMarker(cls, sectionName):
		return cls._sectionmarker[sectionName]

	@classmethod
	def setSectionMarker(cls, sectionName, sectionMarker):
		cls._sectionmarker[sectioName] = sectionMarker

	# symbolsList should be a dictionary of per-section Symbol lists, ex:
	# { ".text" : [S1, S2, etc.], ".data" : [S1, S2, etc.], etc. }
	# arch is an Arch instance
	# Warning: this overwrites the file returned by arch.getLinkerScript()
	@classmethod
	def produceLinkerScript(cls, symbolsList, arch):
		template = arch.getLsTemplate()
		archEnum = arch.getArch()
	
		with open(template, "r") as f:
			lines = f.readlines()

		output_buffer = []
		for line in lines:
			foundMarker = False
			for section in symbolsList.keys():
				if line.startswith(cls.getSectionMarker(section)):
					foundMarker = True
					# Section "openning" part
					output_buffer.append(section + "\t: ALIGN(0x10000)\n")
					output_buffer.append("{\n")
					
					# TODO, is this necessary:
					# output_buffer.append("\t. = ALIGN(0x1000);\n")

					# iterate over symbols to add:
					for symbol in symbolsList[section]:
						# First add padding before if needed
						if not symbol.getReference(archEnum):
							padding_before = symbol.getPaddingBefore(archEnum)
							if padding_before:
								output_buffer.append("\t. = . + " +	
									hex(padding_before) + 
									"; /* padding before "+ 
									symbol.getName() + " */\n")

						# check if the symbol is actually enabled for this arch
						if symbol.getSize(arch.getArch()) >= 0:
							output_buffer.append("\t. = ALIGN(" + 
								str(hex(symbol.getAlignment(archEnum))) + 
								"); /* align for " + symbol.getName() + " */\n")

							output_buffer.append("\t*(" + symbol.getName() +
								"); /* size " + hex(symbol.getSize(archEnum)) +
								" */\n")

						# Then add padding after if needed
						padding_after = symbol.getPaddingAfter(archEnum)
						if padding_after:
							output_buffer.append("\t. = . + " + 
								hex(padding_after) + "; /* padding after " + 
								symbol.getName() + " */\n")

					# Section "closing" part
					output_buffer.append("}\n")

			if not foundMarker:
				output_buffer.append(line)

			with open(arch.getLinkerScript(), "w+") as f:
				for line in output_buffer:
					f.write(line)
