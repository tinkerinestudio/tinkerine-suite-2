"""
Craft is a script to access the plugins which craft a gcode file.

The plugin buttons which are commonly used are bolded and the ones which are rarely used have normal font weight.

"""

from __future__ import absolute_import

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_analyze
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import os
import sys
import time


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getChainText( fileName, procedure ):
	"Get a crafted shape file."
	text=''
	if fileName.endswith('.gcode') or fileName.endswith('.svg'):
		text = archive.getFileText(fileName)
	procedures = getProcedures( procedure, text )
	return getChainTextFromProcedures( fileName, procedures, text )

def getChainTextFromProcedures(fileName, procedures, text):
	'Get a crafted shape file from a list of procedures.'
	lastProcedureTime = time.time()
	for procedure in procedures:
		craftModule = getCraftModule(procedure)
		if craftModule != None:
			text = craftModule.getCraftedText(fileName, text)
			if text == '':
				print('Warning, the text was not recognized in getChainTextFromProcedures in skeinforge_craft for')
				print(fileName)
				return ''
			if gcodec.isProcedureDone( text, procedure ):
				print('%s procedure took %s.' % (procedure.capitalize(), euclidean.getDurationString(time.time() - lastProcedureTime)))
				lastProcedureTime = time.time()
	return text

def getCraftModule(pluginName):
	'Get craft module.'
	return archive.getModuleWithDirectoryPath(getPluginsDirectoryPath(), pluginName)

def getCraftPreferences(pluginName):
	'Get craft preferences.'
	return settings.getReadRepository(getCraftModule(pluginName).getNewRepository()).preferences

def getCraftValue(preferenceName, preferences):
	"Get craft preferences value."
	for preference in preferences:
		if preference.name.startswith(preferenceName):
			return preference.value
	return None

def getLastModule():
	"Get the last tool."
	craftSequence = getReadCraftSequence()
	if len( craftSequence ) < 1:
		return None
	return getCraftModule( craftSequence[-1] )

def getNewRepository():
	'Get new repository.'
	return CraftRepository()

def getPluginFileNames():
	"Get craft plugin fileNames."
	craftSequence = getReadCraftSequence()
	craftSequence.sort()
	return craftSequence

def getPluginsDirectoryPath():
	"Get the plugins directory path."
	return archive.getCraftPluginsDirectoryPath()

def getProcedures(procedure, text):
	'Get the procedures up to and including the given procedure.'
	craftSequence = getReadCraftSequence()
	sequenceIndexFromProcedure = 0
	if procedure in craftSequence:
		sequenceIndexFromProcedure = craftSequence.index(procedure)
	craftSequence = craftSequence[: sequenceIndexFromProcedure + 1]
	for craftSequenceIndex in xrange(len(craftSequence) - 1, -1, -1):
		procedure = craftSequence[craftSequenceIndex]
		if gcodec.isProcedureDone(text, procedure):
			return craftSequence[craftSequenceIndex + 1 :]
	return craftSequence

def getReadCraftSequence():
	"Get profile sequence."
	return skeinforge_profile.getCraftTypePluginModule().getCraftSequence()

def writeChainTextWithNounMessage(fileName, procedure, shouldAnalyze=True):
	'Get and write a crafted shape file.'
	print('')
	print('The %s tool is parsing the file:' % procedure)
	print(os.path.basename(fileName))
	print('')
	startTime = time.time()
	fileNameSuffix = fileName[: fileName.rfind('.')] + '_' + procedure + '.gcode'
	craftText = getChainText(fileName, procedure)
	if craftText == '':
		print('Warning, there was no text output in writeChainTextWithNounMessage in skeinforge_craft for:')
		print(fileName)
		return
	archive.writeFileText(fileNameSuffix, craftText)
	window = None
	if shouldAnalyze:
		window = skeinforge_analyze.writeOutput(fileName, fileNameSuffix, fileNameSuffix, True, craftText)
	print('')
	print('The %s tool has created the file:' % procedure)
	print(fileNameSuffix)
	print('')
	print('It took %s to craft the file.' % euclidean.getDurationString(time.time() - startTime))
	return window

def writeOutput(fileName, shouldAnalyze=True):
	"Craft a gcode file with the last module."
	pluginModule = getLastModule()
	if pluginModule != None:
		return pluginModule.writeOutput(fileName, shouldAnalyze)

def writeSVGTextWithNounMessage(fileName, repository, shouldAnalyze=True):
	'Get and write an svg text and print messages.'
	print('')
	print('The %s tool is parsing the file:' % repository.lowerName)
	print(os.path.basename(fileName))
	print('')
	startTime = time.time()
	fileNameSuffix = fileName[: fileName.rfind('.')] + '_' + repository.lowerName + '.svg'
	craftText = getChainText(fileName, repository.lowerName)
	if craftText == '':
		return
	archive.writeFileText(fileNameSuffix, craftText)
	print('')
	print('The %s tool has created the file:' % repository.lowerName)
	print(fileNameSuffix)
	print('')
	print('It took %s to craft the file.' % euclidean.getDurationString(time.time() - startTime))
	if shouldAnalyze:
		settings.getReadRepository(repository)
		settings.openSVGPage(fileNameSuffix, repository.svgViewer.value)


class CraftRadioButtonsSaveListener(object):
	"A class to update the craft radio buttons."
	def addToDialog( self, gridPosition ):
		"Add this to the dialog."
		euclidean.addElementToListDictionaryIfNotThere( self, self.repository.repositoryDialog, settings.globalProfileSaveListenerListTable )
		self.gridPosition = gridPosition.getCopy()
		self.gridPosition.row = gridPosition.rowStart
		self.gridPosition.increment()
		self.setRadioButtons()

	def getFromRadioPlugins( self, radioPlugins, repository ):
		"Initialize."
		self.name = 'CraftRadioButtonsSaveListener'
		self.radioPlugins = radioPlugins
		self.repository = repository
		repository.displayEntities.append(self)
		return self

	def save(self):
		"Profile has been saved and craft radio plugins should be updated."
		self.setRadioButtons()

	def setRadioButtons(self):
		"Profile has been saved and craft radio plugins should be updated."
		activeRadioPlugins = []
		craftSequence = skeinforge_profile.getCraftTypePluginModule().getCraftSequence()
		gridPosition = self.gridPosition.getCopy()
		isRadioPluginSelected = False
		settings.getReadRepository(self.repository)
		for radioPlugin in self.radioPlugins:
			if radioPlugin.name in craftSequence:
				activeRadioPlugins.append(radioPlugin)
				radioPlugin.incrementGridPosition(gridPosition)
				if radioPlugin.value:
					radioPlugin.setSelect()
					isRadioPluginSelected = True
			else:
				radioPlugin.radiobutton.grid_remove()
		if not isRadioPluginSelected:
			radioPluginNames = self.repository.importantFileNames + [activeRadioPlugins[0].name]
			settings.getSelectedRadioPlugin(radioPluginNames , activeRadioPlugins).setSelect()
		self.repository.pluginFrame.update()


class CraftRepository(object):
	"A class to handle the craft settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_utilities.skeinforge_craft.html', self)
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Craft', self, '')
		self.importantFileNames = ['carve', 'chop', 'feed', 'flow', 'lift', 'raft', 'speed']
		allCraftNames = archive.getPluginFileNamesFromDirectoryPath(getPluginsDirectoryPath())
		self.radioPlugins = settings.getRadioPluginsAddPluginFrame(getPluginsDirectoryPath(), self.importantFileNames, allCraftNames, self)
		CraftRadioButtonsSaveListener().getFromRadioPlugins(self.radioPlugins, self)
		self.executeTitle = 'Craft'

	def execute(self):
		"Craft button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode( self.fileNameInput.value, [], self.fileNameInput.wasCancelled )
		for fileName in fileNames:
			writeOutput(fileName)


def main():
	"Write craft output."
	writeOutput(' '.join(sys.argv[1 :]), False)

if __name__ == "__main__":
	main()
