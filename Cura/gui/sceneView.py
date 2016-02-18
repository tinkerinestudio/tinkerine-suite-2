from __future__ import absolute_import
import re

__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import numpy
import time
import os
import traceback
import threading
import math
import shutil
import fileinput

import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL.GLU import *
from OpenGL.GL import *

from Cura.gui import printWindow
from Cura.gui import expertConfig
from Cura.util import profile
from Cura.util import meshLoader
from Cura.util import objectScene
from Cura.util import resources
from Cura.util import sliceEngine
from Cura.util import sliceEngine2
from Cura.util import removableStorage
from Cura.util import gcodeInterpreter
from Cura.gui.util import previewTools
from Cura.gui.util import opengl
from Cura.gui.util import openglGui
from Cura.util import version

class SceneView(openglGui.glGuiPanel):
	def __init__(self, parent):
		super(SceneView, self).__init__(parent)

		self.varitronicsBrandString = "varitronics"

		self.list = []
		self._pauses = []
		self._konamCode = []

		self.debug = False
		self.busyInfo = None

		self._scene = objectScene.Scene()
		self._gcode = None
		self._counter = 0
		self._gcodeVBOs = []
		self._gcodeFilename = None
		self._gcodeLoadThread = None
		self._objectShader = None
		self._objectLoadShader = None
		self._focusObj = None
		self._selectedObj = None
		self._objColors = [None,None,None,None]
		self._mouseX = -1
		self._mouseY = -1
		self._mouseState = None

		self._yaw = 1054
		self._pitch = 68
		self._zoom = 478
		self._viewTarget = numpy.array([0,0,0], numpy.float32)
		# self._viewTarget[0] = -80
		# self._viewTarget[1] = 206
		self._viewTarget[2] = 90

		self._animView = None
		self._animZoom = None
		self._platformditto = meshLoader.loadMeshes(resources.getPathForMesh('dplus_tm.stl'))[0]##
		self._platformditto._drawOffset = numpy.array([40,0,0], numpy.float32)

		self._platformlitto = meshLoader.loadMeshes(resources.getPathForMesh('litto_tm.stl'))[0]##
		self._platformlitto._drawOffset = numpy.array([40,0,0], numpy.float32)

		self._platformdittopro = meshLoader.loadMeshes(resources.getPathForMesh(_('dpro_tm.stl')))[0]##
		self._platformdittopro._drawOffset = numpy.array([40,0,0], numpy.float32)

		self._isSimpleMode = True

		self._isSlicing = False

		self._anObjectIsOutsidePlatform = False

		self._viewport = None
		self._modelMatrix = None
		self._projMatrix = None
		self.tempMatrix = None

		self._degree = unichr(176)

		self.cameraMode = 'default'

		self.settingsOpen = False
		self.cameraOpen = False
		self.viewmodeOpen = False

		self.advancedOpen = False

		self.saveMenuOpen = False

		self.rotationLock = True

		self.supportLines = []

		self.resultFilename = ""

		xBreakpoint = 1400

		self.showKeyboardShortcuts = False

		self._pauseButtons = []
		self.groupOfTopMenuGroups = []
		self.topmenuGroup = []
		self.groupOfTopMenuGroups.append(self.topmenuGroup)

		self.sliceButton      = openglGui.flexibleGlButton(self, 9, _(''), _('Slice'), (5,0.43), [], self.OnPrintButtonTest, -35, -39, (150,75), "top-right", (245,245,245,255))
		self.sliceButton.setTooltipColour((255,255,255))
		self.sliceButton.setTooltipFontSize(19)
		self.sliceButton.setTooltipFont("roboto-regular.ttf")
		self.sliceButton._hoverHelpText._text = "Preview model\nfor 3D printing"
		self.sliceButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.sliceButton._hoverHelpText.makeText(True)
		self.sliceButton._hoverHelpText._xNudge = -53
		self.sliceButton._hoverHelpText._yNudge = 75
		self.sliceButton._tooltipNudgeY = 23
		self.sliceButton._tooltipNudgeX = 50
		self.sliceButton.setTextAlignment("center")
		self.topmenuGroup.append(self.sliceButton)

		self.abortButton = openglGui.flexibleGlButton(self, 31, "", "Cancel", (1,0.43), [], self.OnAbortButton, -35, -13, (150,25), "top-right", (244,244,244,255))
		self.abortButton.setTooltipColour((255,255,255))
		self.abortButton.setTooltipFontSize(17)
		self.abortButton._tooltipNudgeY = 14
		self.abortButton._tooltipNudgeX = 33
		self.abortButton.setTooltipFont("roboto-medium.ttf")
		self.abortButton.setHidden(True)
		# self.abortButton      = openglGui.flexibleGlButton(self, 10, _(''), _(''), (5,0.43), [], self.OnAbortButton, -35, -38, (150,75), "top-right", (245,245,245,255))

		self.openFileButton      = openglGui.glButton(self, 1, _(''), _(''), (-2.5,-0), self.showLoadModel, -14, -14, 100, "top")
		self.openFileButton._hoverHelpText._text = "Imports 3D models (.STL or .OBJ)."
		self.openFileButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.openFileButton._hoverHelpText.makeText(True)
		self.openFileButton._tooltipNudgeY = 100
		self.openFileButton._tooltipNudgeX = 14
		self.topmenuGroup.append(self.openFileButton)
		self.openFileButton._xBreakpoint = xBreakpoint

		self.resolutionMenuButton      = openglGui.new_age_glRadioButton(self, 2, _('Resolution'), _('Ultra'), (-1.5,-0), self.topmenuGroup, self.noCallback, 0, 0, None, "top", (255,255,255,255))
		self.resolutionMenuButton._hoverHelpText._text = "Adjusts the printing resolution.\n(The higher the resolution, the longer the print will take.)"
		self.resolutionMenuButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.resolutionMenuButton._hoverHelpText.makeText(True)
		self.resolutionMenuButton._tooltipNudgeY = 85
		self.resolutionMenuButton._xBreakpoint = xBreakpoint

		self.infillMenuButton      = openglGui.new_age_glRadioButton(self, 3, _('Infill'), _('Sparse'), (-0.5,-0), self.topmenuGroup, self.noCallback, 0, 0, None, "top", (255,255,255,255))
		self.infillMenuButton._hoverHelpText._text = "Adjusts the density of the model."
		self.infillMenuButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.infillMenuButton._hoverHelpText.makeText(True)
		self.infillMenuButton._tooltipNudgeY = 70
		self.infillMenuButton._xBreakpoint = xBreakpoint

		self.wallMenuButton      = openglGui.new_age_glRadioButton(self, 4, _('Wall'), _('1'), (0.5,0), self.topmenuGroup, self.noCallback, 0, 0, None, "top", (255,255,255,255))
		self.wallMenuButton._hoverHelpText._text = "Adjusts the shell thickness of the model."
		self.wallMenuButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.wallMenuButton._hoverHelpText.makeText(True)
		self.wallMenuButton._tooltipNudgeY = 70
		self.wallMenuButton._xBreakpoint = xBreakpoint

		self.filamentMenuButton      = openglGui.new_age_glRadioButton(self, 5, _('Filament'), _('1.75 mm'), (2.5,-0), self.topmenuGroup, self.noCallback, 0, 0, None, "top", (255,255,255,255))
		self.filamentMenuButton._hoverHelpText._text = "Sets the filament diameter."
		self.filamentMenuButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.filamentMenuButton._hoverHelpText.makeText(True)
		self.filamentMenuButton._tooltipNudgeY = 70
		self.filamentMenuButton._xBreakpoint = xBreakpoint

		self.supportMenuButton      = openglGui.new_age_glRadioButton(self, 6, _('Support'), _('Off'), (1.5,-0), self.topmenuGroup, self.noCallback, 0, 0, None, "top", (255,255,255,255))
		self.supportMenuButton._hoverHelpText._text = "Enables/disables support structure for overhangs."
		self.supportMenuButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.supportMenuButton._hoverHelpText.makeText(True)
		self.supportMenuButton._tooltipNudgeY = 70
		self.supportMenuButton._xBreakpoint = xBreakpoint

		self.speedMenuButton      = openglGui.new_age_glRadioButton(self, 7, _('Speed'), _('100 mm/s'), (3.5,-0), self.topmenuGroup, self.noCallback, 0, 0, None, "top", (255,255,255,255))
		self.speedMenuButton._hoverHelpText._text = "Adjusts the printing speed."
		self.speedMenuButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.speedMenuButton._hoverHelpText.makeText(True)
		self.speedMenuButton._tooltipNudgeY = 70
		self.speedMenuButton._xBreakpoint = xBreakpoint

		self.temperatureMenuButton      = openglGui.new_age_glRadioButton(self, 8, _('Temp'), _('220 C'), (4.5,-0), self.topmenuGroup, self.noCallback, 0, 0, None, "top", (255,255,255,255))
		self.temperatureMenuButton._hoverHelpText._text = "Adjusts the hotend temperature."
		self.temperatureMenuButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.temperatureMenuButton._hoverHelpText.makeText(True)
		self.temperatureMenuButton._tooltipNudgeY = 70
		self.temperatureMenuButton._xBreakpoint = xBreakpoint



		resolutionButtonGroup = []
		self.groupOfTopMenuGroups.append(resolutionButtonGroup)

		self.lowResolutionButton   = openglGui.new_age_flexibleGlRadioButton(self, 0, "", "Low", (-1.5,0.6), resolutionButtonGroup, self.lowResolution, 0, 0, (72,28), "top")
		self.lowResolutionButton._hoverHelpText._text = "300 microns (0.3 mm) per layer"
		self.lowResolutionButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.lowResolutionButton._hoverHelpText.makeText(True)
		self.lowResolutionButton._tooltipNudgeX = 143
		self.lowResolutionButton._tooltipNudgeY = 10
		self.lowResolutionButton._xBreakpoint = xBreakpoint

		self.mediumResolutionButton   = openglGui.new_age_flexibleGlRadioButton(self, 0, "", "Medium", (-1.5,0.92), resolutionButtonGroup, self.medResolution, 0, 0, (72,28), "top")
		self.mediumResolutionButton._hoverHelpText._text = "200 microns (0.2 mm) per layer"
		self.mediumResolutionButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.mediumResolutionButton._hoverHelpText.makeText(True)
		self.mediumResolutionButton._tooltipNudgeX = 143
		self.mediumResolutionButton._tooltipNudgeY = 10
		self.mediumResolutionButton._xBreakpoint = xBreakpoint

		self.highResolutionButton   = openglGui.new_age_flexibleGlRadioButton(self, 0, "", "High", (-1.5,1.24), resolutionButtonGroup, self.highResolution, 0, 0, (72,28), "top")
		self.highResolutionButton.setTooltipFontSize(14)
		self.highResolutionButton._hoverHelpText._text = "100 microns (0.1 mm) per layer"
		self.highResolutionButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.highResolutionButton._hoverHelpText.makeText(True)
		self.highResolutionButton._tooltipNudgeX = 143
		self.highResolutionButton._tooltipNudgeY = 10
		self.highResolutionButton._xBreakpoint = xBreakpoint

		self.fineResolutionButton   = openglGui.new_age_flexibleGlRadioButton(self, 0, "", "Ultra", (-1.5,1.56), resolutionButtonGroup, self.ultraResolution, 0, 0, (72,28), "top")
		self.fineResolutionButton.advancedOnly = True
		self.fineResolutionButton._hoverHelpText._text = "50 microns (0.05 mm) per layer"
		self.fineResolutionButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.fineResolutionButton._hoverHelpText.makeText(True)
		self.fineResolutionButton._tooltipNudgeX = 143
		self.fineResolutionButton._tooltipNudgeY = 10
		self.fineResolutionButton._xBreakpoint = xBreakpoint
		for ctrl in resolutionButtonGroup:
			ctrl.setHidden(True)
		self.resolutionMenuButton.setDependantGroup(resolutionButtonGroup)

		infillButtonGroup = []
		self.groupOfTopMenuGroups.append(infillButtonGroup)
		self.HOLLOW_INFILL_VALUE = 0
		self.SPARSE_INFILL_VALUE = 18
		self.DENSE_INFILL_VALUE = 30

		self.hollowInfillButton = openglGui.new_age_flexibleGlRadioButton(self, 0, "", "Hollow", (-0.5,0.6), infillButtonGroup, lambda infill:self.setInfill(self.HOLLOW_INFILL_VALUE, "Hollow"), 0, 0, (72,28), "top")
		self.hollowInfillButton._hoverHelpText._text = "0% insides filled"
		self.hollowInfillButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.hollowInfillButton._hoverHelpText.makeText(True)
		self.hollowInfillButton._tooltipNudgeX = 95
		self.hollowInfillButton._tooltipNudgeY = 10
		self.hollowInfillButton._xBreakpoint = xBreakpoint

		self.sparseInfillButton = openglGui.new_age_flexibleGlRadioButton(self, 0, "", "Sparse", (-0.5,0.92), infillButtonGroup, lambda infill:self.setInfill(self.SPARSE_INFILL_VALUE, "Sparse"), 0, 0, (72,28), "top")
		self.sparseInfillButton._hoverHelpText._text = "18% insides filled"
		self.sparseInfillButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.sparseInfillButton._hoverHelpText.makeText(True)
		self.sparseInfillButton._tooltipNudgeX = 100
		self.sparseInfillButton._tooltipNudgeY = 10
		self.sparseInfillButton._xBreakpoint = xBreakpoint

		self.denseInfillButton = openglGui.new_age_flexibleGlRadioButton(self, 0, "", "Dense", (-0.5,1.24), infillButtonGroup, lambda infill:self.setInfill(self.DENSE_INFILL_VALUE, "Dense"), 0, 0, (72,28), "top")
		self.denseInfillButton._hoverHelpText._text = "30% insides filled"
		self.denseInfillButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.denseInfillButton._hoverHelpText.makeText(True)
		self.denseInfillButton._tooltipNudgeX = 100
		self.denseInfillButton._tooltipNudgeY = 10
		self.denseInfillButton._xBreakpoint = xBreakpoint
		for ctrl in infillButtonGroup:
			ctrl.setHidden(True)
		self.infillMenuButton.setDependantGroup(infillButtonGroup)

		wallButtonGroup = []
		self.groupOfTopMenuGroups.append(wallButtonGroup)
		self.oneWallButton = openglGui.new_age_flexibleGlRadioButton(self, 0, "", "1", (0.5,0.6), wallButtonGroup, lambda walls:self.setWallThickness(1), 0, 0, (72,28), "top")
		self.oneWallButton._xBreakpoint = xBreakpoint

		self.twoWallButton = openglGui.new_age_flexibleGlRadioButton(self, 0, "", "2", (0.5,0.92), wallButtonGroup, lambda walls:self.setWallThickness(2), 0, 0, (72,28), "top")
		self.twoWallButton._xBreakpoint = xBreakpoint

		self.threeWallButton = openglGui.new_age_flexibleGlRadioButton(self, 0, "", "3", (0.5,1.24), wallButtonGroup, lambda walls:self.setWallThickness(3), 0, 0, (72,28), "top")
		self.threeWallButton._xBreakpoint = xBreakpoint

		self.fourWallButton = openglGui.new_age_flexibleGlRadioButton(self, 0, "", "4", (0.5,1.56), wallButtonGroup, lambda walls:self.setWallThickness(4), 0, 0, (72,28), "top")
		self.fourWallButton._xBreakpoint = xBreakpoint

		for ctrl in wallButtonGroup:
			ctrl.setHidden(True)
		self.wallMenuButton.setDependantGroup(wallButtonGroup)

		filamentButtonGroup = []
		self.groupOfTopMenuGroups.append(filamentButtonGroup)
		self.increaseFilamentButton1 = openglGui.flexibleGlButton(self, 12, "", "", (2.5, 0.6), filamentButtonGroup, self.increaseFilament, 0, 0, (72,28), "top")
		self.increaseFilamentButton1._xBreakpoint = xBreakpoint

		self.filamentLabel =  openglGui.flexibleGLTextLabel(self, 0, "1.75 mm", (2.5, 0.92), filamentButtonGroup, 0, 0, (72,28), "top")
		self.filamentLabel._xBreakpoint = xBreakpoint

		self.decreaseFilamentButton = openglGui.flexibleGlButton(self, 13, "", "", (2.5, 1.24), filamentButtonGroup, self.decreaseFilament, 0, 0, (72,28), "top")
		self.decreaseFilamentButton._xBreakpoint = xBreakpoint

		for ctrl in filamentButtonGroup:
			ctrl.setHidden(True)
		self.filamentMenuButton.setDependantGroup(filamentButtonGroup)

		supportButtonGroup = []
		self.groupOfTopMenuGroups.append(supportButtonGroup)
		self.offSupportButton = openglGui.new_age_flexibleGlRadioButton(self, 0, "", "Off", (1.5,0.6), supportButtonGroup, self.supportOff, 0, 0, (72,28), "top")
		self.offSupportButton._xBreakpoint = xBreakpoint

		self.onSupportButton = openglGui.new_age_flexibleGlRadioButton(self, 0, "", "On", (1.5,0.92), supportButtonGroup, self.supportAll, 0, 0, (72,28), "top")
		self.onSupportButton._xBreakpoint = xBreakpoint

		self.exteriorSupportButton = openglGui.new_age_flexibleGlRadioButton(self, 0, "", "Exterior", (1.5,0.92), supportButtonGroup, self.supportExt, 0, 0, (72,28), "top")
		self.exteriorSupportButton.advancedOnly = True
		self.exteriorSupportButton._hoverHelpText._text = "Generates support only from the print surface."
		self.exteriorSupportButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.exteriorSupportButton._hoverHelpText.makeText(True)
		self.exteriorSupportButton._tooltipNudgeX = 163
		self.exteriorSupportButton._tooltipNudgeY = 10
		self.exteriorSupportButton._xBreakpoint = xBreakpoint

		self.allSupportButton = openglGui.new_age_flexibleGlRadioButton(self, 0, "", "Full", (1.5,1.24), supportButtonGroup, self.supportAll, 0, 0, (72,28), "top")
		self.allSupportButton.advancedOnly = True
		self.allSupportButton._hoverHelpText._text = "Generates support everywhere,\nincluding directly on the model."
		self.allSupportButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.allSupportButton._hoverHelpText.makeText(True)
		self.allSupportButton._tooltipNudgeX = 143
		self.allSupportButton._tooltipNudgeY = 10
		self.allSupportButton._xBreakpoint = xBreakpoint

		for ctrl in supportButtonGroup:
			ctrl.setHidden(True)
		self.supportMenuButton.setDependantGroup(supportButtonGroup)

		speedButtonGroup = []
		self.groupOfTopMenuGroups.append(speedButtonGroup)
		self.increaseSpeedButton1 = openglGui.flexibleGlButton(self, 12, "", "", (3.5, 0.6), speedButtonGroup, self.increasePrintSpeed, 0, 0, (72,28), "top")
		self.increaseSpeedButton1._xBreakpoint = xBreakpoint

		self.speedLabel =  openglGui.flexibleGLTextLabel(self, 0, "70 mm/s", (3.5, 0.92), speedButtonGroup, 0, 0, (72,28), "top")
		self.speedLabel._xBreakpoint = xBreakpoint

		self.decreaseSpeedButton2 = openglGui.flexibleGlButton(self, 13, "", "", (3.5, 1.24), speedButtonGroup, self.decreasePrintSpeed, 0, 0, (72,28), "top")
		self.decreaseSpeedButton2._xBreakpoint = xBreakpoint

		for ctrl in speedButtonGroup:
			ctrl.setHidden(True)
		self.speedMenuButton.setDependantGroup(speedButtonGroup)

		temperatureButtonGroup = []
		self.groupOfTopMenuGroups.append(temperatureButtonGroup)
		self.increaseTemperatureButton1 = openglGui.flexibleGlButton(self, 12, "", "", (4.5, 0.6), temperatureButtonGroup, self.increaseTemperature, 0, 0, (72,28), "top")
		self.increaseTemperatureButton1._xBreakpoint = xBreakpoint

		self.temperatureLabel =  openglGui.flexibleGLTextLabel(self, 0, "220 C", (4.5, 0.92), temperatureButtonGroup, 0, 0, (72,28), "top")
		self.temperatureLabel._xBreakpoint = xBreakpoint

		self.decreaseTemperatureButton1 = openglGui.flexibleGlButton(self, 13, "", "", (4.5, 1.24), temperatureButtonGroup, self.decreaseTemperature, 0, 0, (72,28), "top")
		self.decreaseTemperatureButton1._xBreakpoint = xBreakpoint

		for ctrl in temperatureButtonGroup:
			ctrl.setHidden(True)
		self.temperatureMenuButton.setDependantGroup(temperatureButtonGroup)

		self.modelSelectedButtonGroup = []

		self.duplicateButton = openglGui.flexibleGlButton(self, 27, "", "Duplicate", (1.75, -0.9), self.modelSelectedButtonGroup, self.OnButtonMultiply, 0, 12, (70,70), "bottom", (240,240,240,255))
		self.duplicateButton._hoverOverlayColour = None
		self.duplicateButton._extraHitbox = (-25,25,-25,25)
		self.centerButton = openglGui.flexibleGlButton(self, 28, "", "Center", (2.75, -0.9), self.modelSelectedButtonGroup, self.OnCenter, 0, 12, (70,70), "bottom", (240,240,240,255))
		self.centerButton._hoverOverlayColour = None
		self.centerButton._extraHitbox = (-25,25,-25,25)
		self.layFlatButton = openglGui.flexibleGlButton(self, 29, "", "Lay Flat", (3.75, -0.9), self.modelSelectedButtonGroup, self.OnLayFlat, 0, 12, (70,70), "bottom", (240,240,240,255))
		self.layFlatButton._hoverOverlayColour = None
		self.layFlatButton._extraHitbox = (-25,25,-25,25)
		self.resetButton = openglGui.flexibleGlButton(self, 30, "", "Reset", (4.75, -0.9), self.modelSelectedButtonGroup, self.OnReset, 0, 12, (70,70), "bottom", (240,240,240,255))
		self.resetButton._hoverOverlayColour = None
		self.resetButton._extraHitbox = (-25,25,-25,25)
		self.deleteButton = openglGui.flexibleGlButton(self, 39, "", "Delete", (5.75, -0.9), self.modelSelectedButtonGroup, self.deleteSelection, 0, 12, (70,70), "bottom", (240,240,240,255))
		self.deleteButton._hoverOverlayColour = None
		self.deleteButton._extraHitbox = (-25,25,-25,25)

		self.divider =  openglGui.flexibleGLTextLabel(self, 14, "", (0.95, -0.65), self.modelSelectedButtonGroup, 0, 0, (1,48), "bottom")

		if profile.getPreference('show_advanced') == 'False':
			self.updateAdvancedModeButtonPositions()
			# self.filamentMenuButton.setHidden(True)
			# self.speedMenuButton.setHidden(True)
			# self.temperatureMenuButton.setHidden(True)
			# self.fineResolutionButton.setHidden(True)
			# self.fineResolutionButton.setDisabled(True)
			#
			# self.hollowInfillButton._hoverHelpText._text = ""
			# self.sparseInfillButton._hoverHelpText._text = ""
			# self.denseInfillButton._hoverHelpText._text = ""
			#
			# self.lowResolutionButton._hoverHelpText._text = ""
			# self.mediumResolutionButton._hoverHelpText._text = ""
			# self.highResolutionButton._hoverHelpText._text = ""
			#
			# menuPosNudge = 1
			# for group in self.groupOfTopMenuGroups:
			# 	for element in group:
			# 		pos = element._pos
			# 		element._pos = (pos[0]+menuPosNudge,pos[1])

		self.link1 =  openglGui.flexibleGLTextLabel(self, 14, "", (-2.05, -0.65), self.modelSelectedButtonGroup, 0, 0, (12,2), "bottom")
		self.link2 =  openglGui.flexibleGLTextLabel(self, 14, "", (-0.748, -0.65), self.modelSelectedButtonGroup, 0, 0, (12,2), "bottom")

		self.scaleLabel = openglGui.flexibleGLTextLabel(self, 0, "Scale:", (-4.9, -0.525), self.modelSelectedButtonGroup, 0,0, (0,0), "bottom")

		self.scaleXctrl = openglGui.glNumberCtrl(self, 35, '100', (-3.5, -0.25), lambda value: self.OnScaleEntry(value, 0), True)
		self.modelSelectedButtonGroup.append(self.scaleXctrl)

		# self.scaleYctrl = openglGui.glNumberCtrl(self, '0', (-0.50,-2.17), lambda value: self.OnScaleEntry(value, 1), True)
		# self.scaleList.append(self.scaleYctrl)
		#
		# self.scaleZctrl = openglGui.glNumberCtrl(self, '0', (0.55,-2.17), lambda value: self.OnScaleEntry(value, 2), True)
		# self.scaleList.append(self.scaleZctrl)

		self.scaleXmmctrl = openglGui.glNumberCtrl(self, 33, '10.00', (-2.2, -0.25), lambda value: self.OnScaleEntryMM(value, 0))
		self.modelSelectedButtonGroup.append(self.scaleXmmctrl)

		self.scaleYmmctrl = openglGui.glNumberCtrl(self, 32, '10.00', (-0.9, -0.25), lambda value: self.OnScaleEntryMM(value, 1))
		self.modelSelectedButtonGroup.append(self.scaleYmmctrl)

		self.scaleZmmctrl = openglGui.glNumberCtrl(self, 34, '10.00', (0.4, -0.25), lambda value: self.OnScaleEntryMM(value, 2))
		self.modelSelectedButtonGroup.append(self.scaleZmmctrl)

		self.printPreviewGroup = []
		#self.viewSelection = openglGui.glComboButton(self, 'View mode', '', [7,19,11,15,23], ['Normal', 'Overhang', 'Transparent', 'X-Ray', 'Layers'], (-1,1), self.OnViewChange)
		self.layerSelect = openglGui.glSlider(self, 10000, 0, 1, (-0.5,-0.65), lambda : self.QueueRefresh())
		self.layerSelect._center = "bottom"
		self.printPreviewGroup.append(self.layerSelect)


		self.editButton = openglGui.flexibleGlButton(self, 16, "", "Edit", (3.5, -0.65), self.printPreviewGroup, lambda button: self.setModelView(1), 0, 0, (100,30), "bottom", (255,255,255,255))
		self.editButton.setTooltipColour((255,255,255))
		self.editButton.setTooltipFont("roboto-medium.ttf")

		self.editButton._hoverHelpText._text = "Return to edit slicing settings."
		self.editButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.editButton._hoverHelpText.makeText(True)
		self.editButton._tooltipNudgeX = 10
		self.editButton._tooltipNudgeY = -25

		self.savePrintButton = openglGui.flexibleGlButton(self, 15, "", "Save for Print", (5.5, -0.65), self.printPreviewGroup, self.showSaveModalWindow, 0, 0, (160,30), "bottom", (255,255,255,255))
		self.savePrintButton.setTooltipColour((255,255,255))
		self.savePrintButton.setTooltipFont("roboto-medium.ttf")

		self.clockIcon =  openglGui.flexibleGLTextLabel(self, 25, "", (-6.45, -0.65), self.printPreviewGroup, 0, 0, (80,80), "bottom")
		self.timeEstLabel =  openglGui.flexibleGLTextLabel(self, 0, "Print Time", (-5.7, -0.7), self.printPreviewGroup, 0, 0, (0,0), "bottom", "roboto-light.ttf", (80,80,80), 13)
		self.timeEstLabelTime =  openglGui.flexibleGLTextLabel(self, 0, "00h:00m", (-6.125, -0.425), self.printPreviewGroup, 0, 0, (0,0), "bottom", "roboto-regular.ttf", (80,80,80), 20)
		self.timeEstLabelTime.setTextAlignment("left")


		self.weightIcon =  openglGui.flexibleGLTextLabel(self, 23, "", (-4.4, -0.65), self.printPreviewGroup, 0, 0, (80,80), "bottom")
		self.weightLabel =  openglGui.flexibleGLTextLabel(self, 0, "Filament Usage", (-3.45, -0.7), self.printPreviewGroup, 0, 0, (0,0), "bottom", "roboto-light.ttf", (80,80,80), 13)
		self.weightLabelGrams =  openglGui.flexibleGLTextLabel(self, 0, "00g", (-4.075, -0.425), self.printPreviewGroup, 0, 0, (0,0), "bottom", "roboto-regular.ttf", (80,80,80), 20)
		self.weightLabelGrams.setTextAlignment("left")

		self.divider =  openglGui.flexibleGLTextLabel(self, 14, "", (-2.5, -0.65), self.printPreviewGroup, 0, 0, (1,48), "bottom")
		self.divider2 =  openglGui.flexibleGLTextLabel(self, 14, "", (2.5, -0.65), self.printPreviewGroup, 0, 0, (1,48), "bottom")

		self.infillPlusCounter = 0
		self.infillMinusCounter = 0
		self.infillCounter = int(profile.getProfileSettingFloat('fill_density'))
		self.filamentCounter = float(profile.getProfileSettingFloat('filament_diameter'))

		self.resolutionCounter = int(profile.getProfileSettingFloat('layer_height'))
		self.wallCounter = int(profile.getProfileSettingFloat('wall_thickness'))
		self.supportCounter = int(profile.getProfileSettingFloat('support_angle'))
		self.speedCounter = int(profile.getProfileSettingFloat('print_speed'))
		self.temperatureCounter = int(profile.getProfileSettingFloat('print_temperature'))
		self.temperaturebedCounter = int(profile.getProfileSettingFloat('print_bed_temperature'))

		self.printPreviewLabel = openglGui.flexibleGLTextLabel(self, 0, "Print Preview", (0, 1.5), self.printPreviewGroup, 0, 0, (0,0), "top", "roboto-regular.ttf", (128,128,128), 30)

		self.modelView = 1

		self.insertPauseButton = openglGui.flexibleGlButton(self, 37, '', '', (1.655, -0.67), self.printPreviewGroup, self.onInsertPauseButton, 0, 0, (100,100), "bottom", (240,240,240,255))
		self.insertPauseButton._hoverHelpText._text = "Inserts pause\nat current layer."
		self.insertPauseButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.insertPauseButton._hoverHelpText.makeText(True)
		self.insertPauseButton._tooltipNudgeY = -15
		self.insertPauseButton._tooltipNudgeX = 5
		self.insertPauseButton._extraHitbox = (-15,15,-15,15)

		self.deletePausesButton = openglGui.flexibleGlButton(self, 38, '', '', (2.1, -0.67), self.printPreviewGroup, self.onDeleteAllPausesButton, 0, 0, (100,100), "bottom", (240,240,240,255))
		self.deletePausesButton._hoverHelpText._text = "Resets all pauses."
		self.deletePausesButton._hoverHelpText._backgroundColour = (0,0,255,255)
		self.deletePausesButton._hoverHelpText.makeText(True)
		self.deletePausesButton._tooltipNudgeY = -15
		self.deletePausesButton._extraHitbox = (-15,15,-15,15)

		self.modalTest = openglGui.glModal(self, (0,0)) #Important to make this before the rest of the elements!
		self.modalAfterSave = openglGui.glModal(self, (0,0)) #Important to make this before the rest of the elements!

		saveModalGroup = []

		self.whiteBackground =  openglGui.flexibleGlButton(self, 11, "", "", (0, 4), saveModalGroup, self.noCallback, 0, 0, (460,250), "top")
		self.whiteBackground._hoverOverlayColour = None

		self.saveToSdCardButton = openglGui.flexibleGlButton(self, 40, "", "", (0, 4), saveModalGroup, self.onModalCopyToSD, -115, -18, (70,70), "top", None)
		self.saveToSdCardButton._altHighlightImage = 18
		self.saveToSdCardButton._extraHitbox = (-115,115,-70,140)

		# self.saveToDirectoryButton = openglGui.flexibleGlButton(self, 11, "", "", (0, 4), saveModalGroup, self.onModalSaveToDirectory, 115, 40, (230,250), "top", (245,245,245,255))
		self.saveToDirectoryButton = openglGui.flexibleGlButton(self, 20, "", "", (0, 4), saveModalGroup, self.onModalSaveToDirectory, 115, -15, (70,70), "top", None)
		self.saveToDirectoryButton._altHighlightImage = 24
		self.saveToDirectoryButton._extraHitbox = (-115,115,-70,140)
		# self.sdCardIcon =  openglGui.flexibleGLTextLabel(self, 18, "SD Card", (-1.55, 3.62), saveModalGroup, 0, 35, (80,80), "top", "roboto-regular.ttf", (128,128,128), 20)
		self.sdCardText3 =  openglGui.flexibleGLTextLabel(self, 19, "Sd Card", (-1.6, 4.5), saveModalGroup, 0, 0, (0,0), "top", "roboto-regular.ttf", (128,128,128), 20)
		self.sdCardText1 =  openglGui.flexibleGLTextLabel(self, 19, "After saving, insert the SD", (-1.65, 4.9), saveModalGroup, 0, 0, (0,0), "top", "roboto-light.ttf", (128,128,128), 16)
		self.sdCardText2 =  openglGui.flexibleGLTextLabel(self, 19, "card into the printer to print", (-1.65, 5.1), saveModalGroup, 0, 0, (0,0), "top", "roboto-light.ttf", (128,128,128), 16)

		# self.folderIcon =  openglGui.flexibleGLTextLabel(self, 20, "Computer", (1.55, 3.62), saveModalGroup, 0, 35, (80,80), "top", "roboto-regular.ttf", (128,128,128), 20)
		self.folderText3 =  openglGui.flexibleGLTextLabel(self, 19, "Computer", (1.6, 4.5), saveModalGroup, 0, 0, (0,0), "top", "roboto-regular.ttf", (128,128,128), 20)
		self.folderText1 =  openglGui.flexibleGLTextLabel(self, 19, "To be transfered to an SD", (1.6, 4.9), saveModalGroup, 0, 0, (0,0), "top", "roboto-light.ttf", (128,128,128), 16)
		self.folderText2 =  openglGui.flexibleGLTextLabel(self, 19, "card or another device", (1.6, 5.1), saveModalGroup, 0, 0, (0,0), "top", "roboto-light.ttf", (128,128,128), 16)

		self.saveToSdCardButtonOverlay = openglGui.flexibleGlButton(self, 11, "", "", (0, 4), saveModalGroup, self.onModalCopyToSD, -115, 0, (230,250), "top", None)
		self.saveToSdCardButtonOverlay.buttonUnselectedColour = (255,255,255, 150)

		self.saveToLabel =  openglGui.flexibleGlButton(self, 16, "", "Save To...", (0, 2.83), saveModalGroup, self.noCallback, 0, -3, (456,38), "top",  (255,255,255,255))
		self.saveToLabel.setTooltipFont("roboto-regular.ttf")
		self.saveToLabel.setTooltipFontSize(20)
		self.saveToLabel.setTooltipColour((255,255,255))
		self.saveToLabel._hoverOverlayColour = None
		self.closeModalButton = openglGui.flexibleGlButton(self, 17, "", "", (2.9, 3), saveModalGroup, self.modalTest.closeModal, 0, -18, (25,25), "top", (245,245,245,255))

		self.modalDivider =  openglGui.flexibleGLTextLabel(self, 14, "", (0, 4.2), saveModalGroup, 0, 0, (1,160), "top")


		self.modalTest.setElements(saveModalGroup)
		self.modalTest.closeModal()


		afterSaveModalGroup = []

		self.whiteBackground =  openglGui.flexibleGlButton(self, 11, "", "", (0, 4), afterSaveModalGroup, self.noCallback, 0, 20, (460,290), "top")

		self.backToPrintPreviewButton = openglGui.flexibleGlButton(self, 16, "", "Back to Print Preview", (-1.4, 5.5), afterSaveModalGroup, self.onModalBackToPrintPreview, 0, 0, (175,30), "top", (255,255,255,255))
		self.backToPrintPreviewButton.setTooltipColour((255,255,255))
		self.backToPrintPreviewButton.setTooltipFontSize(16)
		self.backToPrintPreviewButton.setTooltipFont("roboto-regular.ttf")

		self.newProjectButton = openglGui.flexibleGlButton(self, 15, "", "New Project", (1.4, 5.5), afterSaveModalGroup, self.onModalNewProject, 0, 0, (175,30), "top", (255,255,255,255))
		self.newProjectButton.setTooltipColour((255,255,255))
		self.newProjectButton.setTooltipFontSize(16)
		self.newProjectButton.setTooltipFont("roboto-regular.ttf")


		self.saveToLabel =  openglGui.flexibleGlButton(self, 16, "", "Save To...", (0, 2.83), afterSaveModalGroup, self.noCallback, 0, -3, (456,38), "top",  (255,255,255,255))
		self.saveToLabel.setTooltipFont("roboto-regular.ttf")
		self.saveToLabel.setTooltipFontSize(20)
		self.saveToLabel.setTooltipColour((255,255,255))
		self.saveToLabel._hoverOverlayColour = None
		self.closeModalButton = openglGui.flexibleGlButton(self, 17, "", "", (2.9, 3), afterSaveModalGroup, self.modalAfterSave.closeModal, 0, -18, (25,25), "top", (245,245,245,255))

		self.ejectSDButton = openglGui.flexibleGlButton(self, 26, "", "", (-1.5, 4.75), afterSaveModalGroup, self.OnEjectModal, 0, 0, (50,50), "top", None)
		self.ejectSDButton._altHighlightImage = 41
		# self.ejectSDButton._tooltipTextTitle._yNudge += 30

		self.savedIcon =  openglGui.flexibleGLTextLabel(self, 21, "Successfully saved the filename", (0.01, 3.2), afterSaveModalGroup, 0, 35, (70,70), "top", "roboto-regular.ttf", (128,128,128), 20)
		self.savedIcon.setTooltipColour((140,198,63))

		self.savedText1 =  openglGui.flexibleGLTextLabel(self, 19, "Please eject the SD card and\ninsert it into the printer to print", (-1.2, 5), afterSaveModalGroup, 0, 0, (0,0), "top", "roboto-light.ttf", (128,128,128), 16)
		self.savedText1.setTextAlignment("left")

		self.savedText2 =  openglGui.flexibleGLTextLabel(self, 19, " ", (0, 5), afterSaveModalGroup, 0, 0, (0,0), "top", "roboto-light.ttf", (128,128,128), 16)
		self.ejectedMessage = "You can now safely remove the SD card.\n Please insert it into the printer to print."

		self.modalAfterSave.setElements(afterSaveModalGroup)
		self.modalAfterSave.closeModal()

		self.startTourGroup = []
		self.endTourGroup = []
		self.tourGroup = []

		self.whiteBackground2 =  openglGui.flexibleGlButton(self, 11, "", "", (0, 0), [], self.noCallback, 0, 0, (2000,2000), "top", (255,255,255,255))
		self.whiteBackground2._hoverOverlayColour = None
		self.whiteBackground2.setDisabled(True)
		self.whiteBackground2.setHidden(True)

		# self.greyBackground =  openglGui.flexibleGlButton(self, 11, "", "", (0, 0), [], self.closeKeyboardShortcuts, 0, 0, (2000,2000), "top", (50,50,50,100))
		self.greyBackground =  openglGui.flexibleGlButton(self, 11, "", "", (0, 0), [], self.noCallback, 0, 0, (4000,2000), "top", (50,50,50,100))
		self.greyBackground._hoverOverlayColour = None
		self.greyBackground.setDisabled(True)
		self.greyBackground.setHidden(True)

		self.closeKeyboardShortcutsButton =  openglGui.flexibleGlButton(self, 19, "", "", (5.8, 0), [], self.closeKeyboardShortcuts, 0, 0, (20,20), "top", (255,255,255,255))
		self.closeKeyboardShortcutsButton.setDisabled(True)
		self.closeKeyboardShortcutsButton.setHidden(True)

		self.skipTour =  openglGui.flexibleGlButton(self, 11, "", "Skip for now", (-1.3, 4.3), self.startTourGroup, self.stopTour, 0, 0, (180,50), "top", (241,130,90,255))
		self.skipTour.buttonUnselectedColour = (241,130,90,255)
		self.skipTour.setTooltipColour((255,255,255,255))
		self.skipTour.setTooltipFontSize(20)
		self.skipTour.setTooltipFont('roboto-regular.ttf')
		self.skipTour._tooltipText._yNudge = -7
		self.skipTour.setDisabled(True)
		self.skipTour.setHidden(True)

		self.startTour =  openglGui.flexibleGlButton(self, 11, "", "Start the tour", (1.3, 4.3), self.startTourGroup, self.incrementTour, 0, 0, (180,50), "top", (140,198,63,255))
		self.startTour.buttonUnselectedColour = (140,198,63,255)
		self.startTour.setTooltipColour((255,255,255,255))
		self.startTour.setTooltipFontSize(20)
		self.startTour.setTooltipFont('roboto-regular.ttf')
		self.startTour._tooltipText._yNudge = -7
		self.startTour.setDisabled(True)
		self.startTour.setHidden(True)

		self.previousTour =  openglGui.flexibleGlButton(self, 11, "", "Back", (-0.6, 1.6), self.tourGroup, self.decrementTour, 0, 0, (80,30), "top", (140,140,140,255))
		self.previousTour.buttonUnselectedColour = (128,128,128,255)
		self.previousTour.setTooltipColour((255,255,255,255))
		self.previousTour.setTooltipFontSize(15)
		self.previousTour.setTooltipFont('roboto-regular.ttf')
		self.previousTour.setDisabled(True)
		self.previousTour.setHidden(True)

		self.nextTour =  openglGui.flexibleGlButton(self, 11, "", "Next", (0.6, 1.6), self.tourGroup, self.incrementTour, 0, 0, (80,30), "top", (140,198,63,255))
		self.nextTour.buttonUnselectedColour = (140,198,63,255)
		self.nextTour.setTooltipColour((255,255,255,255))
		self.nextTour.setTooltipFontSize(15)
		self.nextTour.setTooltipFont('roboto-regular.ttf')
		self.nextTour.setDisabled(True)
		self.nextTour.setHidden(True)

		self.skipTourText =  openglGui.flexibleGlButton(self, 11, "", "Skip the Tour", (0.75, 2), self.tourGroup, self.stopTour, 0, 0, (95,25), "top", (255,198,63,120))
		self.skipTourText.buttonUnselectedColour = (140,198,63,0)
		self.skipTourText.setTooltipColour((241,130,90,255))
		self.skipTourText.setDisabled(True)
		self.skipTourText.setHidden(True)

		self.feelingReadyText =  openglGui.flexibleGLTextLabel(self, 19, "Feeling Ready? ", (-0.6, 2.115), self.tourGroup, 0, 0, (0,0), "top", "roboto-light.ttf", (128,128,128), 15)
		self.feelingReadyText.setDisabled(True)
		self.feelingReadyText.setHidden(True)

		self.endTour =  openglGui.flexibleGlButton(self, 11, "", "Get Started", (0, 5), self.endTourGroup, self.stopTour, 0, -11, (190,60), "top", (140,198,63,255))
		self.endTour.buttonUnselectedColour = (140,198,63,255)
		self.endTour.setTooltipColour((255,255,255,255))
		self.endTour.setTooltipFontSize(21)
		self.endTour.setTooltipFont('roboto-regular.ttf')
		self.endTour.setDisabled(True)
		self.endTour.setHidden(True)

		self._slicer = sliceEngine.Slicer(self._updateSliceProgress)
		self._engine = sliceEngine2.Engine(self._updateEngineProgress)
		self._sceneUpdateTimer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self._onRunSlicer, self._sceneUpdateTimer)
		self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
		self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)

		self.initalizeSettingLabels()
		self.OnViewChange()
		self.OnToolSelect(0)
		self.updateToolButtons()
		self.updateProfileToControls()

	def decrementTour(self, e):
		self.tourCount -= 1
		self._drawGui()

	def incrementTour(self, e):
		self.tourCount += 1
		self._drawGui()

	def stopTour(self, e):
		profile.putPreference('first_run_tour_done', 'True')
		self.whiteBackground2.setHidden(True)
		self.whiteBackground2.setDisabled(True)
		for item in self.tourGroup:
			item.setHidden(True)
			item.setDisabled(True)
		for item in self.startTourGroup:
			item.setHidden(True)
			item.setDisabled(True)
		for item in self.endTourGroup:
			item.setHidden(True)
			item.setDisabled(True)
		mainWindow = self.GetParent().GetParent()
		mainWindow.SetMaxSize((10000,10000))
		mainWindow.SetMinSize((1024,768))
		mainWindow.SetSize((1024,768))

	def closeKeyboardShortcuts(self, e):
		self.showKeyboardShortcuts = False
		self.greyBackground.setHidden(True)
		self.closeKeyboardShortcutsButton.setHidden(True)

	def updateAdvancedModeButtonPositions(self):

		if profile.getPreference('show_advanced') == 'False':
			menuPosNudge = 1
			self.filamentMenuButton.setHidden(True)
			self.speedMenuButton.setHidden(True)
			self.temperatureMenuButton.setHidden(True)
			self.fineResolutionButton.setDisabled(True)
			self.resolutionMenuButton.setSelected(False)

			self.hollowInfillButton._hoverHelpText._text = ""
			self.sparseInfillButton._hoverHelpText._text = ""
			self.denseInfillButton._hoverHelpText._text = ""

			self.lowResolutionButton._hoverHelpText._text = ""
			self.mediumResolutionButton._hoverHelpText._text = ""
			self.highResolutionButton._hoverHelpText._text = ""
		else:
			menuPosNudge = -1
			self.filamentMenuButton.setHidden(False)
			self.speedMenuButton.setHidden(False)
			self.temperatureMenuButton.setHidden(False)
			self.fineResolutionButton.setDisabled(False)
			self.resolutionMenuButton.setSelected(False)

			self.hollowInfillButton._hoverHelpText._text = "0% density"
			self.sparseInfillButton._hoverHelpText._text = "18% density"
			self.denseInfillButton._hoverHelpText._text = "30% density"

			self.lowResolutionButton._hoverHelpText._text = "300 microns (0.3 mm) per layer"
			self.mediumResolutionButton._hoverHelpText._text = "200 microns (0.2 mm) per layer"
			self.highResolutionButton._hoverHelpText._text = "100 microns (0.1 mm) per layer"

		for group in self.groupOfTopMenuGroups:
			for element in group:
				pos = element._pos
				element._pos = (pos[0]+menuPosNudge,pos[1])
		self._container.updateLayout()

	def showSaveModalWindow(self, e):
		self.modalTest.showModal()
		if profile.getPreference('sdpath') != '':
			print profile.getPreference('sdpath')
		else:
			print "theres no sd card!"

	def onModalCopyToSD(self, e):
		if len(removableStorage.getPossibleSDcardDrives()) == 0:
			print "There is no sd card!"
			return
		self.OnCopyToSD(e)
		self.modalTest.closeModal(e)

		self.savedIcon._imageID = 21
		self.savedText1.setTooltipText("Please eject the SD card and\ninsert it into the printer to print")
		self.savedText2.setTooltipText("")
		self.savedIcon.setTooltipText(self.resultFilename + " successfully saved")
		self.sceneUpdated()
		self.modalAfterSave.showModal(e)


	def onModalNewProject(self, e):
		if self.OnDeleteAll(e):
			self.modalAfterSave.closeModal(e)
  			self.setModelView(1)

	def onModalSaveToDirectory(self, e):
		if self.OnCopyToDirectory(e):
			self.modalTest.closeModal(e)
			self.savedIcon._imageID = 22
			self.savedText1.setTooltipText("")
			self.savedText2.setTooltipText("Please load the file onto an\n   SD card before printing.")
			self.savedIcon.setTooltipText(self.resultFilename + " successfully saved")
			self.sceneUpdated()
			self.modalAfterSave.showModal(e)

	def onModalBackToPrintPreview(self, e):
		self.modalAfterSave.closeModal(e)

	def initalizeSettingLabels(self):
		layerHeight = profile.getProfileSettingFloat('layer_height')
		infill = profile.getProfileSettingFloat('fill_density')
		walls = profile.getProfileSettingFloat('wall_thickness')
		filamentDiameter = profile.getProfileSettingFloat('filament_diameter')
		support = profile.getProfileSetting('support')
		printSpeed = profile.getProfileSettingFloat('print_speed')
		printTemperature = profile.getProfileSettingFloat('print_temperature')

		if layerHeight == 0.3:
			self.resolutionMenuButton.setTooltipText("Low")
			self.lowResolutionButton.setSelected(True)
		elif layerHeight == 0.2:
			self.resolutionMenuButton.setTooltipText("Medium")
			self.mediumResolutionButton.setSelected(True)
		elif layerHeight == 0.1:
			self.resolutionMenuButton.setTooltipText("High")
			self.highResolutionButton.setSelected(True)
		elif layerHeight == 0.05:
			self.resolutionMenuButton.setTooltipText("Ultra")
			self.fineResolutionButton.setSelected(True)
		else:
			self.resolutionMenuButton.setTooltipText(str(layerHeight))

		if infill == self.HOLLOW_INFILL_VALUE:
			self.infillMenuButton.setTooltipText("Hollow")
			self.hollowInfillButton.setSelected(True)
		elif infill == self.SPARSE_INFILL_VALUE:
			self.infillMenuButton.setTooltipText("Sparse")
			self.sparseInfillButton.setSelected(True)
		elif infill == self.DENSE_INFILL_VALUE:
			self.infillMenuButton.setTooltipText("Dense")
			self.denseInfillButton.setSelected(True)
		else:
			self.infillMenuButton.setTooltipText(str(infill))

		if walls == 1:
			self.oneWallButton.setSelected(True)
		elif walls == 2:
			self.twoWallButton.setSelected(True)
		elif walls == 3:
			self.threeWallButton.setSelected(True)
		elif walls == 4:
			self.fourWallButton.setSelected(True)
		self.wallMenuButton.setTooltipText(str(int(walls)))

		if support == "Everywhere":
			if profile.getPreference('show_advanced') == 'False':
				self.onSupportButton.setSelected(True)
				self.supportMenuButton.setTooltipText("On")
			else:
				self.allSupportButton.setSelected(True)
				self.supportMenuButton.setTooltipText("Full")
		elif support == "Exterior Only":
			self.exteriorSupportButton.setSelected(True)
			self.supportMenuButton.setTooltipText("Exterior")
		else:
			self.offSupportButton.setSelected(True)
			self.supportMenuButton.setTooltipText("Off")

		self.filamentMenuButton.setTooltipText(str(filamentDiameter) + " mm")
		self.filamentLabel.setTooltipText(str(filamentDiameter) + " mm")
		self.speedMenuButton.setTooltipText(str(int(printSpeed)) + " mm/s")
		self.speedLabel.setTooltipText(str(int(printSpeed)) + " mm/s")
		self.temperatureMenuButton.setTooltipText(str(int(printTemperature)) + self._degree + "C")
		self.temperatureLabel.setTooltipText(str(int(printTemperature)) + self._degree + "C")

		# self.filamentMenuButton      = openglGui.new_age_glRadioButton(self, 5, _('Filament'), _('1.75 mm'), (1.5,-0), topmenuGroup, self.noCallback, 0, 0, None, "top", True)
		# self.supportMenuButton      = openglGui.new_age_glRadioButton(self, 6, _('Support'), _('Off'), (2.5,-0), topmenuGroup, self.noCallback, 0, 0, None, "top", True)
		# self.speedMenuButton      = openglGui.new_age_glRadioButton(self, 7, _('Speed'), _('100 mm/s'), (3.5,-0), topmenuGroup, self.noCallback, 0, 0, None, "top", True)
		# self.temperatureMenuButton      = openglGui.new_age_glRadioButton(self, 8, _('Temp'), _('220 C'), (4.5,-0), topmenuGroup, self.noCallback, 0, 0, None, "top", True)

	def noCallback(self, button):
		# print "no callback"
		pass

	def setModelView(self, value):
		self.modelView = value
		self.OnViewChange()
	def getModelView(self):
		return self.modelView

	def showSettings(self, e):
		#print "Yaw: " + str(self._yaw)
		#print "Pitch: " + str(self._pitch)
		#print "Zoom: " + str(self._zoom)
		#print "viewTarget[0]: " + str(self._viewTarget[0])
		#print "viewTarget[1]: " + str(self._viewTarget[1])

		if self.settingsOpen == True:
			self.settingsOpen = False
		else:
			self.settingsOpen = True
		self.CloseSavePrompt(e)
	def saveSettings(self, e):
		profile.putProfileSetting('fill_density', int(self.infillCounter))
		profile.putProfileSetting('filament_diameter', float(self.filamentCounter))
		profile.putProfileSetting('wall_thickness', int(self.wallCounter))
		profile.putProfileSetting('support_angle', int(self.supportCounter))
		profile.putProfileSetting('print_speed', int(self.speedCounter))
		profile.putProfileSetting('print_temperature', int(self.temperatureCounter))
		profile.putProfileSetting('print_bed_temperature', int(self.temperaturebedCounter))

		self.updateProfileToControls()
		#self.infillCounter = 0
		self.savedLabel._timer = 30
	def showAdvancedSettings(self, button):

		if self.advancedOpen == True:
			self.advancedOpen = False
			button.setImageID(17)
		else:
			self.advancedOpen = True
			button.setImageID(16)
	def showCamera(self,e):
		if self.cameraOpen == True:
			self.cameraOpen = False
		else:
			self.cameraOpen = True
		self.OnToolSelect(0)
	def showViewmode(self,e):
		self.cameraButton._selected = False
		self.cameraOpen = False
		if self.viewmodeOpen == True:
			self.viewmodeOpen = False
		else:
			self.viewmodeOpen = True
		self.OnToolSelect(0)
	def showRotate(self,e):
		self.setModelView(1)
		self.cameraButton._selected = False
		self.cameraOpen = False
		self.moveButton._selected = False #this is the viewmode button
		self.viewmodeOpen = False

		#if self.viewmodeOpen == True:
		#	self.viewmodeOpen = False
		#else:
		#	self.viewmodeOpen = True
		self.OnToolSelect(e)
	def showScale(self,e):
		self.setModelView(1)
		self.cameraButton._selected = False
		self.cameraOpen = False
		self.moveButton._selected = False #this is the viewmode button
		self.viewmodeOpen = False

		#if self.viewmodeOpen == True:
		#	self.viewmodeOpen = False
		#else:
		#	self.viewmodeOpen = True
		self.OnToolSelect(e)

	def showLoadModel(self, button = 1):
		# print "Yaw: " + str(self._yaw)
		# print "Pitch: " + str(self._pitch)
		# print "Zoom: " + str(self._zoom)
		# print "viewTarget[0]: " + str(self._viewTarget[0])
		# print "viewTarget[1]: " + str(self._viewTarget[1])
		if button == 1:
			dlg=wx.FileDialog(self, _('Import 3D Model'), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST|wx.FD_MULTIPLE)
			dlg.SetWildcard(meshLoader.loadWildcardFilter() + "|GCode file (*.gcode)|*.g;*.gcode;*.G;*.GCODE")
			if dlg.ShowModal() != wx.ID_OK:
				dlg.Destroy()
				return
			filenames = dlg.GetPaths()
			dlg.Destroy()
			if len(filenames) < 1:
				return False
			for filename in filenames:
				ext = filename[filename.rfind('.')+1:].upper()
				if ext == "EXPERTPASS":
					ecw = expertConfig.expertConfigWindow(self)
					ecw.Centre()
					ecw.Show(True)
					return
			profile.putPreference('lastFile', filenames[0])
			gcodeFilename = None
			for filename in filenames:
				self.GetParent().GetParent().addToModelMRU(filename)
				ext = filename[filename.rfind('.')+1:].upper()
				if ext == 'G' or ext == 'GCODE':
					gcodeFilename = filename
			if gcodeFilename is not None:
				if self._gcode is not None:
					self._gcode = None
					for layerVBOlist in self._gcodeVBOs:
						for vbo in layerVBOlist:
							self.glReleaseList.append(vbo)
					self._gcodeVBOs = []
				self._gcode = gcodeInterpreter.gcode()
				self._gcodeFilename = gcodeFilename
				self.setModelView(4)
				self.OnSliceDone(gcodeFilename, False)
				self.OnViewChange()
			else:
				if self.getModelView() == 4:
					self.setModelView(1)
					self.OnViewChange()
				try:
					self.loadScene(filenames)
				except:
					pass

	def testgcodeload(self,filename):
		self.busyInfo = wx.BusyInfo(_("loading gcode... please wait..."), self)
		gcodeFilename = filename
		self.supportLines = []
		if self._gcode is not None:
			self._gcode = None
			for layerVBOlist in self._gcodeVBOs:
				for vbo in layerVBOlist:
					self.glReleaseList.append(vbo)
				self._gcodeVBOs = []
		self._gcode = gcodeInterpreter.gcode()
		self._gcodeFilename = gcodeFilename

		try:
			print_found = False
			weight_found = False
			if os.path.isfile(filename):
				self._engine._result = sliceEngine2.EngineResult()
				with open(filename, "r") as f:
					# print_found = False
					# weight_found = False
					for line in f:
						line.strip()
						if 'Print time:' in line:
							# print "found it!"
							# print line
							# print (int(line.split(':')[1].strip()) * 60 * 60) + (int(line.split(':')[2].strip()) * 60)
							self._engine._result._printTimeSeconds = (int(line.split(':')[1].strip()) * 60 * 60) + (int(line.split(':')[2].strip()) * 60)
						 	print_found = True
						if 'Print weight:' in line:
							gramStringWithG = line.split(':')[1]
							gramString = re.sub("[^0123456789\.]","", gramStringWithG)
							self.weightLabelGrams.setTooltipText("%sg" % (gramString))
							weight_found = True
						if print_found == True and weight_found == True:
							break

				with open(filename, "r") as f:
					self._engine._result.setGCode(f.read())
				self._engine._result.setFinished(True)
				# print "loaded gcode from file"

				self._gcode.load(self._engine._result._gcodeData)

				result = self._engine.getResult()
				timeText = '%s' % (result.getPrintTime())
				weightTextGrams = '%.0f' % (result.getFilamentWeight()*1000)

				time = timeText.split(':')

				hours = time[0]
				minutes = time[1]

				self.timeEstLabelTime.setTooltipText("%sh:%sm" % (hours, minutes))
				# self.weightLabelGrams.setTooltipText("%sg" % (weightTextGrams))
		except:
			pass
			# print "could not load from file in path"




		self._pauses = self._gcode.pauses

		for item in self._pauseButtons:
			item._hidden = True
			item._disabled = True
			item._pos = -100,-100

		self._pauseButtons = []

		self.setModelView(4)
		for pause in self._pauses:
			self.addPause(pause)

		self.busyInfo = None
		self._OnSize('')

	def addPause(self, pause):
		slider = self.layerSelect
		pos = slider._pos

		if slider._maxValue-slider._minValue != 0:
			valueNormalized = (float(pause-slider._minValue)/(slider._maxValue-slider._minValue))
		else:
			valueNormalized = 0

		w, h = slider.getMinSize()

		pauseButton = openglGui.flexibleGlButton(self, 36, "", "", (pos[0], pos[1]), self._pauseButtons, self.noCallback, w*valueNormalized - w/2, 9, (32,32), "bottom")
		# pauseButton.setDisabled(True)
		self.printPreviewGroup.append(pauseButton)
		self._OnSize('')
		# pauseButton._altHighlightImage = 35
		# pauseButton = openglGui.flexibleGlButton(self, pausez, "", "", (1.5, pausez), self._pauseButtons, lambda n=pausez: self.onDeletePauseButton(pausez), 0, 0, (72,28), "top")
		# pauseButton.layerNumber = pausez

	def showSaveModel(self):
		if len(self._scene.objects()) < 1:
			return


		defPath = profile.getPreference('lastFile')
		defPath = defPath[0:defPath.rfind('.')] + '_export' + '.stl'

		dlg=wx.FileDialog(self, _('Save 3D model'), os.path.split(profile.getPreference('lastFile'))[0], defPath, style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
		dlg.SetWildcard(meshLoader.saveWildcardFilter())
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return
		filename = dlg.GetPath()
		dlg.Destroy()
		busyInfo = wx.BusyInfo(_("Saving model(s), please wait..."), self)
		meshLoader.saveMeshes(filename, self._scene.objects())
		busyInfo.Destroy()

	def OnPrintButton(self, button):
		if len(self._scene.objects()) < 1:
			return
		if self.getProgressBar() is not None:
			return
		if not self._anObjectIsOutsidePlatform:
			return
		self.setModelView(0)
		defPath = profile.getPreference('lastFile')
		defPath = defPath[0:defPath.rfind('.')] + '.g'

		#dlg=wx.FileDialog(self, "Save project gcode file", os.path.split(profile.getPreference('lastFile'))[0], defPath, style=wx.FD_SAVE)
		#dlg.SetWildcard("GCode file (*.g, *.gcode)|*.g;*.gcode;*.G;*.GCODE")
		#if dlg.ShowModal() != wx.ID_OK:
		#	dlg.Destroy()
		#	return
		#resultFilename = dlg.GetPath()
		resultFilename = defPath
		#dlg.Destroy()
		self.saveSettings(button)
		self._isSlicing = True

		self.setCursorToBusy()
		self._slicer.runSlicer(self._scene.objects(), resultFilename, self)
		#self.setProgressBar(0.001)
		self.abortButton._hidden = False

		#smw = sliceMenu.sliceMenu(self)
		#smw.Centre()
		#smw.Show(True)

	def OnPrintButtonTest(self, button):
		if len(self._scene.objects()) < 1:
			dial = wx.MessageDialog(None, "There doesn't seem to be anything on the build platform!\nFirst Import your model file then click slice again.", "Error encountered during Slice", wx.OK|wx.ICON_EXCLAMATION)
			dial.ShowModal()
			dial.Destroy()
			return
		if self.getProgressBar() is not None:
			return
		if not self._anObjectIsOutsidePlatform:
			dial = wx.MessageDialog(None, "A model is outside the build platform. Models that are outside the\nplatform will appear grey. Please move the models until they appear green.", "Error encountered during Slice", wx.OK|wx.ICON_EXCLAMATION)
			dial.ShowModal()
			dial.Destroy()
			return
		self.setModelView(1)
		for element in self.topmenuGroup:
			element.setDisabled(True)
		defPath = profile.getPreference('lastFile')
		defPath = defPath[0:defPath.rfind('.')] + '.g'
		self.setCursorToBusy()
		#dlg=wx.FileDialog(self, "Save project gcode file", os.path.split(profile.getPreference('lastFile'))[0], defPath, style=wx.FD_SAVE)
		#dlg.SetWildcard("GCode file (*.g, *.gcode)|*.g;*.gcode;*.G;*.GCODE")
		#if dlg.ShowModal() != wx.ID_OK:
		#	dlg.Destroy()
		#	return
		#resultFilename = dlg.GetPath()
		# resultFilename = defPath
		#dlg.Destroy()
		# self.saveSettings(button)
		self._isSlicing = True

		result = self._engine.getResult()
		finished = result is not None and result.isFinished()
		if finished:
			result.setFinished(False)
		self._engine.runEngine(self._scene)
		#self.setProgressBar(0.001)
		self.abortButton.setHidden(False)

		self.sliceButton.setImageID(15)
		self.sliceButton.setTooltipText("Slicing...")
		self.sliceButton._tooltipNudgeY = 12
		self.sliceButton._tooltipNudgeX = 35
		# self.sliceButton.setHidden(True)

	def setSliceButtonMode(self):
		self.sliceButton.setImageID(9)
		self.sliceButton.setTooltipText("Slice")
		self.sliceButton._tooltipText.makeText(True)
		self.sliceButton._tooltipNudgeY = 23
		self.sliceButton._tooltipNudgeX = 50


	def onInsertPauseButton(self, button=1):
		currentLayer = (int(self.layerSelect.getValue())-1)
		# print ";LAYER:%i" % currentLayer
		added = False
		defPath = profile.getPreference('lastFile')
		defPath = defPath[0:defPath.rfind('.')] + '.g'

		for line in fileinput.input(defPath, inplace = 1):
			print line,
			if added == False:
				if getCodeInt(line, 'G') == 1:
					extruderPosition = getCodeFloat(line, 'E')
				if line.startswith(";LAYER:%i" % currentLayer):
					extruderPosition -= 2
					print ";BEGIN-PAUSE\nG91\nG1 Z50 E-50 F2000\nG90\nG1 X100 Y100 F1500\nM84 X Y E\nG92 E%.5f\nM25\n;END-PAUSE" % extruderPosition
					added = True
		# if added == True:
		# 	print "I added it!"
		# else:
		# 	print "didn't add anything!"
		self.testgcodeload(defPath)

		# self.addPause(currentLayer)
		# self.saveStatusText._label = "Pause added at Layer:%i" % int(self.layerSelect.getValue())

	def onDeleteAllPausesButton(self, button=1):
		foundPause = False
		removedPausesCounter = 0
		defPath = profile.getPreference('lastFile')
		defPath = defPath[0:defPath.rfind('.')] + '.g'
		for line in fileinput.input(defPath, inplace = 1):
			if line.startswith(";BEGIN-PAUSE"):
				foundPause = True
				removedPausesCounter += 1
			elif foundPause == False:
				print line,
			if line.startswith(";END-PAUSE"):
				foundPause = False
		for item in self._pauseButtons:
			item._hidden = True
			item._disabled = True
			item._pos = -100,-100

		self.testgcodeload(defPath)
		# self.saveStatusText._label = "Removed %i pauses from gcode" % removedPausesCounter

	def onDeletePauseButton(self, layerNumber):
		print layerNumber
		# layerNumber = button.layerNumber
		for x in range (0, len(self._pauseButtons)):
			try:
				if self._pauseButtons[x].layerNumber == layerNumber:
					self._pauseButtons[x]._hidden = True
					del self._pauseButtons[x]
					break
			except:
				pass



	def setCursorToBusy(self):
		mainWindow = self.GetParent().GetParent()
		mainWindow.setCursorToBusy()

	def setCursorToDefault(self):
		mainWindow = self.GetParent().GetParent()
		mainWindow.setCursorToDefault()


	def OnAbortButton(self, button):
		#self.setProgressBar(None)
		try:
			self._engine.abortEngine()
			self.abortButton.setHidden(True)
			self.abortButton.setProgressBar(None)
			self.sliceButton.setHidden(False)
			for element in self.topmenuGroup:
				element.setDisabled(False)
			self.setSliceButtonMode()
			# self._slicer._pspw.OnAbort(button)
		except:
			print "abort failed"
		self.setCursorToDefault()
		#self.setProgressBar(None)

	def showPrintWindow(self):
		if self._gcodeFilename is None:
			return
		printWindow.printFile(self._gcodeFilename)
		if self._gcodeFilename == self._slicer.getGCodeFilename():
			self._slicer.submitSliceInfoOnline()

	def showSaveGCode(self):
		defPath = profile.getPreference('lastFile')
		defPath = defPath[0:defPath.rfind('.')] + '.gcode'
		dlg=wx.FileDialog(self, _('Save toolpath'), defPath, style=wx.FD_SAVE)
		dlg.SetFilename(self._scene._objectList[0].getName())
		dlg.SetWildcard('Toolpath (*.gcode)|*.gcode;*.g')
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return
		filename = dlg.GetPath()
		dlg.Destroy()

		threading.Thread(target=self._copyFile,args=(self._gcodeFilename, filename)).start()

	def OnSliceDone(self, resultFilename, saveFile=True):
		self._selectedObj = None
		defPath = profile.getPreference('lastFile')
		defPath = defPath[0:defPath.rfind('.')] + '.g'
		if saveFile == True:
			self.busyInfo = wx.BusyInfo(_("saving gcode... please wait..."), self)
			# self._saveGCode(defPath)
			t1 = threading.Thread(target=self._saveGCode,args=(defPath,))
			t1.start()
			t1.join()
			# self._saveGCode(defPath)
			self.busyInfo = False
		self.setSliceButtonMode()
		self.testgcodeload(resultFilename)

		# self.loadGcodeFromEngine(resultFilename)
		self.setProgressBar(None)
		# self.saveMenuOpen = True
		# self.sdSaveButton._hidden = False
		self.setCursorToDefault()
		#self.sdEjectButton._hidden = False
		# self.directorySaveButton._hidden = False
		# self.closeSaveButton._hidden = False
		# self.saveText._hidden = False
		# self.saveStatusText._hidden = False
		# self.saveStatusText._label = ""
		self.setCursorToDefault()

		gcode = self._engine.getResult()
		printTimeSeconds = gcode._printTimeSeconds

		if printTimeSeconds != None:
			printTimeMinutes = printTimeSeconds / 60
		else:
			printTimeMinutes = 0

		# self.printTimeEstimationText._label = "Est. Print time - %02dh:%02dm | Weight: %.2fg" % (int(printTimeMinutes / 60), int(printTimeMinutes % 60), self._gcode.calculateWeight()*1000)
		# if version.isDevVersion():
		# 	try:
		# 		for settingPair in self._gcode.basicSettings:
		# 			self.saveStatusText._label += settingPair
		# 	except:
		# 		print "could not find setting pair"
  		# self.printTimeEstimationText._hidden = False
		# self.resultFilename = resultFilename
		# self.settingsOpen = False
		#text = "Would you like to copy the sliced file to SD card: [" + profile.getPreference('sdpath') + "]?"

		# if saveFile == True:
			# self.busyInfo = wx.BusyInfo(_("saving gcode... please wait..."), self)
			# threading.Thread(target=self._saveGCode,args=(defPath,)).start()
			# self._saveGCode(defPath)
			# self.busyInfo = False
		# self.cameraMode = 'right'
		# self.cameraChange()
		self._selectedObj = None
	def _saveGCode(self, targetFilename, ejectDrive = False):
		gcode = self._engine.getResult().getGCode()
		try:
			size = float(len(gcode))
			read_pos = 0
			with open(targetFilename, 'wb') as fdst:
				while 1:
					buf = gcode.read(16*1024)
					if len(buf) < 1:
						break
					read_pos += len(buf)
					fdst.write(buf)
					# self.printButton.setProgressBar(read_pos / size)
					self._queueRefresh()
		except:
			import sys, traceback
			traceback.print_exc()
			#self.notification.message("Failed to save")
		#else:
			#if ejectDrive:
				#self.notification.message("Saved as %s" % (targetFilename), lambda : self._doEjectSD(ejectDrive), 31, 'Eject')
			# elif explorer.hasExplorer():
			# 	self.notification.message("Saved as %s" % (targetFilename), lambda : explorer.openExplorer(targetFilename), 4, 'Open folder')
			#else:
				#self.notification.message("Saved as %s" % (targetFilename))
		# self.printButton.setProgressBar(None)
		# self._engine.getResult().submitInfoOnline()

	def OnCopyToSD(self, e):
		if profile.getPreference('sdpath') != '':

			defPath = profile.getPreference('lastFile')
			defPath = defPath[0:defPath.rfind('.')] + '.g'

			busyInfo = wx.BusyInfo(_("saving to sd... please wait..."), self)
			sdPath = profile.getPreference('sdpath')
			filename = os.path.basename(defPath)

			self.resultFilename = filename

			if profile.getPreference('sdshortnames') == 'True':
				filename = self.getShortFilename(filename)
			try:
				# self._saveGCode(os.path.join(sdPath, filename))
				#threading.Thread(target=self._saveGCode,args=(os.path.join(sdPath, filename),)).start()
				shutil.copy(defPath, os.path.join(profile.getPreference('sdpath'), filename))
				# self.saveStatusText._label = str(filename) + " saved to [" + str(profile.getPreference('sdpath')) +"]"
			except:
				print "could not save to sd card"
				return False
				# self.saveStatusText._label = _("Unable to save to SD Card")
		else:
			return False

	def getShortFilename(self,filename):
		ext = filename[filename.rfind('.'):]
		filename = filename[: filename.rfind('.')]
		return filename[:8] + ext[:2]

	def OnCopyToDirectory(self, e):
		defPath = profile.getPreference('lastFile')
		defPath = defPath[0:defPath.rfind('.')] + '.g'

		filename = os.path.basename(defPath)
		#print self.resultFilename

		dlg=wx.FileDialog(self, _("Save project gcode file"), os.path.split(defPath)[0], filename, style=wx.FD_SAVE | wx.OVERWRITE_PROMPT)
		dlg.SetWildcard("GCode file (*.g, *.gcode)|*.g;*.gcode;*.G;*.GCODE")
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return False
		path = dlg.GetPath()
		self.resultFilename = os.path.basename(path)
		#self.resultFilename = dlg.GetPath()
		#resultFilename = defPath
		dlg.Destroy()
		busyInfo = wx.BusyInfo(_("saving to directory... please wait..."), self)
		try:
			# threading.Thread(target=self._saveGCode,args=(path,)).start()
			shutil.copy2(defPath, path)
			# self.saveStatusText._label = dlg.GetFilename() + _(" saved to directory")
			# print "copied " + filename + " into directory"
		except:
			traceback.print_exc()
			#print "could not shutil the file: " + path + " to directory"
			# self.saveStatusText._label = _("File Already Exists in Directory")
			#print 'My exception occurred, value:', e.value
		return True

	def OnEjectModal(self, e):
		self.savedText1.setTooltipText("")
		self.savedText1._tooltipText.makeText(True)

		self.savedText2.setTooltipText(self.ejectedMessage)
		self.savedText2._tooltipText.makeText(True)

		# self.ejectSDButton._hidden = True

		self.OnSafeRemove(e)
		self._OnSize('')
		self.Refresh()

	def OnSafeRemove(self, e):
		try:
			if len(removableStorage.getPossibleSDcardDrives()) != 0 and profile.getPreference('sdpath'):
				removableStorage.ejectDrive(profile.getPreference('sdpath'))
				print "sd card ejected"
				# self.saveStatusText._label = _("SD Card Ejected")

		except:
			print "could not eject sd"
			# self.saveStatusText._label = _("Unable to Eject SD Card")
	def CloseSavePrompt(self, e):
		self.saveMenuOpen = False
		self.sdSaveButton._hidden = True
		self.sdEjectButton._hidden = True
		self.directorySaveButton._hidden = True
		self.closeSaveButton._hidden = True
		self.saveText._hidden = True
		self.saveStatusText._hidden = True
		self.printTimeEstimationText._hidden = True
		self.saveStatusText._label = ""
	def _copyFile(self, fileA, fileB, allowEject = False):
		try:
			size = float(os.stat(fileA).st_size)
			with open(fileA, 'rb') as fsrc:
				with open(fileB, 'wb') as fdst:
					while 1:
						buf = fsrc.read(16*1024)
						if not buf:
							break
						fdst.write(buf)
						# self.printButton.setProgressBar(float(fsrc.tell()) / size)
						self._queueRefresh()
		except:
			import sys
			print sys.exc_info()
		# 	self.notification.message(_("Failed to save"))
		# else:
		# 	if allowEject:
		# 		self.notification.message("Saved as %s" % (fileB), lambda : self.notification.message('You can now eject the card.') if removableStorage.ejectDrive(allowEject) else self.notification.message('Safe remove failed...'))
		# 	else:
		# 		self.notification.message("Saved as %s" % (fileB))
		# self.printButton.setProgressBar(None)
		if fileA == self._slicer.getGCodeFilename():
			self._slicer.submitSliceInfoOnline()

	def _showSliceLog(self):
		dlg = wx.TextEntryDialog(self, "The slicing engine reported the following", "Engine log...", '\n'.join(self._slicer.getSliceLog()), wx.TE_MULTILINE | wx.OK | wx.CENTRE)
		dlg.ShowModal()
		dlg.Destroy()

	def OnToolSelect(self, button):
		# if self.rotateToolButton.getSelected():
		self.tool = previewTools.toolScale(self)
		self.tool2 = previewTools.toolRotate(self)
		# elif self.scaleToolButton.getSelected():
		# 	self.tool = previewTools.toolScale(self)
		# 	self.tool2 = previewTools.toolRotate(self)

		#elif self.mirrorToolButton.getSelected():
		#	self.tool = previewTools.toolNone(self)
		# else:
		# 	self.tool = previewTools.toolNone(self)
		# 	self.tool2 = previewTools.toolNone(self)
		# self.resetRotationButton.setHidden(not self.rotateToolButton.getSelected())
		# self.layFlatButton.setHidden(not self.rotateToolButton.getSelected())

		# for item in self.scaleList:
		# 	item.setHidden(not self.scaleToolButton.getSelected())
		# for item in self.rotateList:
		# 	item.setHidden(not self.rotateToolButton.getSelected())
		#
		# for item in self.viewModeList:
		# 	item.setHidden(not self.viewmodeOpen)
		# for item in self.cameraList:
		# 	item.setHidden(not self.scaleToolButton.getSelected())


		# self.resetScaleButton.setHidden(not self.scaleToolButton.getSelected())
		# self.rotationLockButton.setHidden(not self.scaleToolButton.getSelected())
		#self.resetScaleButton.setHidden(True)
		#self.scaleMaxButton.setHidden(not self.scaleToolButton.getSelected())
		# self.scaleMaxButton.setHidden(True)
		#self.scaleForm.setHidden(not self.scaleToolButton.getSelected())
		# self.scaleForm.setHidden(True)
		#self.mirrorXButton.setHidden(not self.mirrorToolButton.getSelected())
		#self.mirrorYButton.setHidden(not self.mirrorToolButton.getSelected())
		#self.mirrorZButton.setHidden(not self.mirrorToolButton.getSelected())
		# self.mirrorXButton.setHidden(True)
		# self.mirrorYButton.setHidden(True)
		# self.mirrorZButton.setHidden(True)
	def updateToolButtons(self):
		if self._selectedObj is None:
			hidden = True
		else:
			hidden = False
		#self.rotateToolButton.setHidden(hidden)
		#self.scaleToolButton.setHidden(hidden)
		#self.mirrorToolButton.setHidden(hidden)
		if hidden:
			# self.rotateToolButton.setSelected(False)
			# self.scaleToolButton.setSelected(False)
			#self.mirrorToolButton.setSelected(False)
			self.OnToolSelect(0)
	def SetDisableForGroup(self, group, boolean):
		for element in group:
			element.setDisabled(boolean)
			try:
				element.setSelected(False)
			except:
				pass

	def OnViewChange(self):
		if self.getModelView() == 4:
			self.viewMode = 'gcode'
			if self._gcode is not None and self._gcode.layerList is not None:
				self.layerSelect.setRange(1, len(self._gcode.layerList) - 1)
			self._selectObject(None)
			# self.gcodeViewButton.setSelected(True)
			# self.overhangViewButton.setSelected(False)
			# self.modelViewButton.setSelected(False)

			self.SetDisableForGroup(self.topmenuGroup, True)
		elif self.getModelView() == 1:
			self.viewMode = 'overhang'
			# self.gcodeViewButton.setSelected(False)
			# self.overhangViewButton.setSelected(True)
			# self.modelViewButton.setSelected(False)

			self.SetDisableForGroup(self.topmenuGroup, False)
		elif self.getModelView() == 2:
			self.viewMode = 'transparent'
		elif self.getModelView() == 3:
			self.viewMode = 'xray'
		else:
			self.viewMode = 'normal'
			# self.gcodeViewButton.setSelected(False)
			# self.overhangViewButton.setSelected(False)
			# self.modelViewButton.setSelected(True)
		# self.layerSelect.setHidden(self.viewMode != 'gcode')
		# self.insertPauseButton.setHidden(self.viewMode != 'gcode')
		# self.deletePausesButton.setHidden(self.viewMode != 'gcode')
		# self.editButton.setHidden(self.viewMode != 'gcode')
		# self.savePrintButton.setHidden(self.viewMode != 'gcode')
		# self.timeEstLabel.setHidden(self.viewMode != 'gcode')
		# self.timeEstLabelTime.setHidden(self.viewMode != 'gcode')

		for element in self.printPreviewGroup:
			element.setHidden(self.viewMode != 'gcode')
		self.QueueRefresh()

	def OnRotateReset(self, button):
		if self._selectedObj is None:
			return
		self._selectedObj.resetRotation()
		# self._scene.pushFree()
		self._selectObject(self._selectedObj)
		self.sceneUpdated()

	def OnLayFlat(self, button):
		if self._selectedObj is None:
			return
		self._selectedObj.layFlat()
		# self._scene.pushFree()
		self._selectObject(self._selectedObj)
		self.sceneUpdated()

	def OnScaleReset(self, button):
		if self._selectedObj is None:
			return
		self._selectedObj.resetScale()
		self._selectObject(self._selectedObj)
		self.updateProfileToControls()
		self.sceneUpdated()

	def OnReset(self, button):
		if self._selectedObj is None:
			return
		self._selectedObj.resetScale()
		self._selectedObj.resetRotation()
		self._selectObject(self._selectedObj)
		self.updateProfileToControls()
		self.sceneUpdated()

	def OnRotationLock(self, button):
		if button.getImageID() == 32:
			self.rotationLock = False
			button.setImageID(33)
		else:
			button.setImageID(32)
			self.rotationLock = True
		self.sceneUpdated()


	def OnScaleMax(self, button):
		if self._selectedObj is None:
			return
		self._selectedObj.scaleUpTo(self._machineSize - numpy.array(profile.calculateObjectSizeOffsets() + [0.0], numpy.float32) * 2 - numpy.array([1,1,1], numpy.float32))
		self._scene.pushFree()
		self._selectObject(self._selectedObj)
		self.updateProfileToControls()
		self.sceneUpdated()
	def supportOnOff(self, button):
		if button.getImageID() == 9:
			profile.putProfileSetting('support', 'Exterior Only')
			button.setImageID(10)
		else:
			profile.putProfileSetting('support', 'None')
			button.setImageID(9)

	def supportOff(self, button):
		profile.putProfileSetting('support', 'None')
		self.supportMenuButton.setTooltipText('Off')

	def supportExt(self, button):
		profile.putProfileSetting('support', 'Exterior Only')
		self.supportMenuButton.setTooltipText('Exterior')

	def supportAll(self, button):
		profile.putProfileSetting('support', 'Everywhere')
		if profile.getPreference('show_advanced') == 'True':
			self.supportMenuButton.setTooltipText('Full')
		else:
			self.supportMenuButton.setTooltipText('On')


	def vaseOnOff(self, button):
		if button.getImageID() == 9:
			button.setImageID(10)
			#print profile.getProfileSettingFloat('fill_density')
			profile.putProfileSetting('temp_infill', profile.getProfileSettingFloat('fill_density'))
			profile.putProfileSetting('fill_density', '0')
			profile.putProfileSetting('vase', 'True')
			profile.putProfileSetting('top_surface_thickness_layers', '0')
			self.infillText.setTooltip(str(int(profile.getProfileSettingFloat('fill_density'))) + '%')
			self.sceneUpdated()

		else:
			button.setImageID(9)
			#profile.putProfileSetting('temp_infill', )
			profile.putProfileSetting('fill_density', profile.getProfileSettingFloat('temp_infill'))
			profile.putProfileSetting('vase', 'False')
			profile.putProfileSetting('top_surface_thickness_layers', profile.getProfileSettingDefault('top_surface_thickness_layers'))
			self.infillText.setTooltip(str(int(profile.getProfileSettingFloat('fill_density'))) + '%')
			self.sceneUpdated()

	def changeToCustom(self, e):
		profile.putPreference('machine_width',profile.getProfileSettingFloat('custom_machine_width'))
		profile.putPreference('machine_depth', profile.getProfileSettingFloat('custom_machine_depth'))
		profile.putPreference('machine_height', profile.getProfileSettingFloat('custom_machine_height'))
		self.machineText.setTooltip('Custom 3D Printer')
		self.sceneUpdated()
		self.updateProfileToControls()

	def brimOn(self, e):
		profile.putProfileSetting('skirt_gap', '0')
		profile.putProfileSetting('skirt_line_count', '5')

	def brimOff(self, e):
		profile.putProfileSetting('skirt_gap', '3')
		profile.putProfileSetting('skirt_line_count', '3')

	def changeToLitto(self, e):
		profile.putPreference('machine_width', '130')
		profile.putPreference('machine_depth', '120')
		profile.putPreference('machine_height', '175')
		# self.machineText.setTooltip('Litto 3D Printer')
		self.sceneUpdated()
		self.updateProfileToControls()

	def changeToDitto(self, e):
		profile.putPreference('machine_width', '210')
		profile.putPreference('machine_depth', '180')
		profile.putPreference('machine_height', '230')
		# self.machineText.setTooltip('Ditto+ 3D Printer')
		self.sceneUpdated()
		self.updateProfileToControls()

	def changeToDittoPro(self, e):
		profile.putPreference('machine_width', '215')
		profile.putPreference('machine_depth', '160')
		profile.putPreference('machine_height', '220')
		# self.machineText.setTooltip(_('DittoPro 3D Printer'))
		self.sceneUpdated()
		self.updateProfileToControls()

	def lowResolution(self, e):
		profile.putProfileSetting('layer_height', '0.3')
		profile.putProfileSetting('edge_width_mm', '0.40')
		# profile.putProfileSetting('print_flow', '0.94')
		profile.putProfileSetting('print_flow', '1')
		profile.putProfileSetting('infill_width', '0.4')
		profile.putProfileSetting('bridge_feed_ratio', '100')
		profile.putProfileSetting('bridge_flow_ratio', '105')

		#profile.putProfileSetting('perimeter_flow_ratio', '75')

		profile.putProfileSetting('top_surface_thickness_layers', '3')

		self.resolutionMenuButton.setTooltipText("Low")
		self.sceneUpdated()
		self.updateProfileToControls()
	def medResolution(self, e):
		profile.putProfileSetting('layer_height', '0.2')
		profile.putProfileSetting('edge_width_mm', '0.40')
		profile.putProfileSetting('print_flow', '1')
		#profile.putProfileSetting('edge_width_mm', '0.15')
		profile.putProfileSetting('infill_width', '0.4')
		profile.putProfileSetting('bridge_feed_ratio', '100')
		profile.putProfileSetting('bridge_flow_ratio', '105')

		#profile.putProfileSetting('perimeter_flow_ratio', '75')

		profile.putProfileSetting('top_surface_thickness_layers', '3')

		self.resolutionMenuButton.setTooltipText("Medium")
		self.sceneUpdated()
		self.updateProfileToControls()

	def highResolution(self, e):
		profile.putProfileSetting('layer_height', '0.1')
		profile.putProfileSetting('edge_width_mm', '0.4')
		profile.putProfileSetting('print_flow', '1')
		#profile.putProfileSetting('edge_width_mm', '0.15') #220

		profile.putProfileSetting('infill_width', '0.4')
		profile.putProfileSetting('bridge_feed_ratio', '90')
		profile.putProfileSetting('bridge_flow_ratio', '155')

		#profile.putProfileSetting('perimeter_flow_ratio', '75')

		profile.putProfileSetting('top_surface_thickness_layers', '6')

		self.resolutionMenuButton.setTooltipText("High")
		self.sceneUpdated()
		self.updateProfileToControls()

	def ultraResolution(self, e):

		profile.putProfileSetting('layer_height', '0.05')
		profile.putProfileSetting('edge_width_mm', '0.40')
		#profile.putProfileSetting('edge_width_mm', '0.15') //220
		# profile.putProfileSetting('print_flow', '1.20') #20% increase
		#profile.putProfileSetting('bottom_thickness', '0.15')

		profile.putProfileSetting('infill_width', '0.4')
		profile.putProfileSetting('bridge_feed_ratio', '90')
		profile.putProfileSetting('bridge_flow_ratio', '150')

		#profile.putProfileSetting('perimeter_flow_ratio', '75')

		profile.putProfileSetting('top_surface_thickness_layers', '12')

		self.resolutionMenuButton.setTooltipText("Ultra")
		self.sceneUpdated()
		self.updateProfileToControls()

	def setInfill(self, infill, text):
		self.infillCounter = int(infill)
		self.infillMenuButton.setTooltipText(str(text))
		profile.putProfileSetting('fill_density', float(infill))
		self.sceneUpdated()
		self.updateProfileToControls()

	def decreaseInfill(self, e):
		if profile.getProfileSetting('vase') == 'True':
			return	#TODO: put popup saying vase is enabled therefore infill is set to 0. disable vase to change infill settings.
		if int(self.infillCounter) > 0:
			#profile.putProfileSetting('fill_density', profile.getProfileSettingFloat('fill_density')-1)
			self.infillPlusCounter = 0
			self.infillMinusCounter +=1
			if 5 < self.infillMinusCounter < 10:
				self.infillCounter -= 2
			elif 11 < self.infillMinusCounter:
				self.infillCounter -= 5
			else:
				self.infillCounter -= 1
			if self.infillCounter < 0:
				self.infillCounter = 0
			self.infillText.setTooltip(str(self.infillCounter) + '%')
			self.sceneUpdated()
			self.updateProfileToControls()

	def increaseInfill(self, e):
		if profile.getProfileSetting('vase') == 'True':
			return #TODO: put popup saying vase is enabled therefore infill is set to 0. disable vase to change infill settings.
		if int(self.infillCounter) < 100:
			#profile.putProfileSetting('fill_density', profile.getProfileSettingFloat('fill_density')+1)

			self.infillPlusCounter += 1
			self.infillMinusCounter = 0
			if 5 < self.infillPlusCounter < 10:
				self.infillCounter += 2
			elif 11 < self.infillPlusCounter:
				self.infillCounter += 5
			else:
				self.infillCounter += 1
			if self.infillCounter > 100:
				self.infillCounter = 100
			self.infillText.setTooltip(str(self.infillCounter) + '%')

			#self.infillText.setTooltip(str(int(profile.getProfileSettingFloat('fill_density'))) + '%')
			self.sceneUpdated()
			self.updateProfileToControls()


	def	decreaseFilament(self, e):
		if float(self.filamentCounter) > 1.65:
			self.filamentCounter -= 0.01
			profile.putProfileSetting('filament_diameter', self.filamentCounter)
			self.filamentLabel.setTooltipText(str(self.filamentCounter) + " mm" )
			self.filamentMenuButton.setTooltipText(str(self.filamentCounter) + " mm" )

			self.sceneUpdated()
			self.updateProfileToControls()

	def	increaseFilament(self, e):
		if float(self.filamentCounter) < 1.85:
			self.filamentCounter += 0.01
			profile.putProfileSetting('filament_diameter', self.filamentCounter)
			self.filamentLabel.setTooltipText(str(self.filamentCounter) + " mm" )
			self.filamentMenuButton.setTooltipText(str(self.filamentCounter) + " mm" )

			self.sceneUpdated()
			self.updateProfileToControls()

	def setFilament(self, value):
		profile.putProfileSetting('filament_diameter', value)
		self.filamentCounter = value
		self.filamentLabel.setTooltipText(str(self.filamentCounter) + " mm" )
		self.filamentMenuButton.setTooltipText(str(self.filamentCounter) + " mm" )


	def setWallThickness(self, walls):
		self.wallCounter = int(walls)
		self.wallMenuButton.setTooltipText(str(walls))
		profile.putProfileSetting('wall_thickness', int(walls))
		self.sceneUpdated()
		self.updateProfileToControls()

	def decreaseWallThickness(self, e):
		if int(self.wallCounter) > 1:
			self.wallCounter -= 1
			#profile.putProfileSetting('wall_thickness', profile.getProfileSettingFloat('wall_thickness')-1)
			self.shellText.setTooltip(str(self.wallCounter))
			self.sceneUpdated()
			self.updateProfileToControls()
		#getProfileSetting
	def increaseWallThickness(self, e):
		self.wallCounter += 1
		#profile.putProfileSetting('wall_thickness', profile.getProfileSettingFloat('wall_thickness')+1)
		self.shellText.setTooltip(str(self.wallCounter))
		#self.shellText.setTooltip(str(int(profile.getProfileSettingFloat('wall_thickness'))))
		self.sceneUpdated()
		self.updateProfileToControls()
		#getProfileSetting

	def decreaseSupport(self, e):
		if int(self.supportCounter) > 1:
			self.supportCounter -= 1
			#profile.putProfileSetting('wall_thickness', profile.getProfileSettingFloat('wall_thickness')-1)
			self.supportText.setTooltip(str(self.supportCounter)+self._degree )
			profile.putProfileSetting('support_angle', int(self.supportCounter))
			self.sceneUpdated()
			self.updateProfileToControls()
		#getProfileSetting
	def increaseSupport(self, e):
		self.supportCounter += 1
		#profile.putProfileSetting('wall_thickness', profile.getProfileSettingFloat('wall_thickness')+1)
		self.supportText.setTooltip(str(self.supportCounter)+self._degree )
		#self.shellText.setTooltip(str(int(profile.getProfileSettingFloat('wall_thickness'))))
		profile.putProfileSetting('support_angle', int(self.supportCounter))
		self.sceneUpdated()
		self.updateProfileToControls()
		#getProfileSetting

	def decreasePrintSpeed(self, e):
		if int(self.speedCounter) > 30:
			self.speedCounter -= 5
			profile.putProfileSetting('print_speed', self.speedCounter)
			self.speedLabel.setTooltipText(str(self.speedCounter) + " mm/s" )
			self.speedMenuButton.setTooltipText(str(self.speedCounter) + " mm/s" )
			self.sceneUpdated()
			self.updateProfileToControls()
		#getProfileSetting

	def increasePrintSpeed(self, e):
		if int(self.speedCounter) < 120:
			self.speedCounter += 5
			profile.putProfileSetting('print_speed', self.speedCounter)
			self.speedLabel.setTooltipText(str(self.speedCounter) + " mm/s" )
			self.speedMenuButton.setTooltipText(str(self.speedCounter) + " mm/s" )

			self.sceneUpdated()
			self.updateProfileToControls()
		#getProfileSetting

	def setPrintSpeed(self, value):
		profile.putProfileSetting('print_speed',value)
		self.speedCounter = value
		self.speedLabel.setTooltipText(str(self.speedCounter) + " mm/s" )
		self.speedMenuButton.setTooltipText(str(self.speedCounter) + " mm/s" )

		self.sceneUpdated()
		self.updateProfileToControls()

	def decreaseTemperature(self, e):
		if int(self.temperatureCounter) > 170:
			self.temperatureCounter -= 5
			profile.putProfileSetting('print_temperature', self.temperatureCounter)

			self.temperatureLabel.setTooltipText(str(int(self.temperatureCounter)) + self._degree + "C")
			self.temperatureMenuButton.setTooltipText(str(int(self.temperatureCounter)) + self._degree + "C")

			self.sceneUpdated()
			self.updateProfileToControls()

	def increaseTemperature(self, e):
		if int(self.temperatureCounter) < 240:
			self.temperatureCounter += 5
			profile.putProfileSetting('print_temperature', self.temperatureCounter)
			self.temperatureLabel.setTooltipText(str(int(self.temperatureCounter)) + self._degree + "C")
			self.temperatureMenuButton.setTooltipText(str(int(self.temperatureCounter)) + self._degree + "C")
			self.sceneUpdated()
			self.updateProfileToControls()

	def setTemperature(self, value):
		self.temperatureCounter = value
		profile.putProfileSetting('print_temperature', self.temperatureCounter)
		self.temperatureLabel.setTooltipText(str(int(self.temperatureCounter)) + self._degree + "C")
		self.temperatureMenuButton.setTooltipText(str(int(self.temperatureCounter)) + self._degree + "C")

	def decreaseBedTemperature(self, e):
		if int(self.temperaturebedCounter) > 0:
			#profile.putProfileSetting('print_bed_temperature', profile.getProfileSettingFloat('print_bed_temperature')-5)
			self.temperaturebedCounter -= 5
			self.bedTemperatureText.setTooltip(str(int(self.temperaturebedCounter)) + self._degree + "C")
			self.sceneUpdated()
			self.updateProfileToControls()
	def increaseBedTemperature(self, e):
		if int(self.temperaturebedCounter) < 150:
			#profile.putProfileSetting('print_bed_temperature', profile.getProfileSettingFloat('print_bed_temperature')+5)
			self.temperaturebedCounter += 5
			self.bedTemperatureText.setTooltip(str(int(self.temperaturebedCounter)) + self._degree + "C")
			self.sceneUpdated()
			self.updateProfileToControls()

	#def OnSettingChange(self, e):
	#	if self.type == 'profile':
	#		profile.putProfileSetting(self.configName, self.GetValue())
	#	else:
	#		profile.putPreference(self.configName, self.GetValue())

	def OnMirror(self, axis):
		if self._selectedObj is None:
			return
		self._selectedObj.mirror(axis)
		self.sceneUpdated()

	def OnScaleEntry(self, value, axis):
		if self._selectedObj is None:
			return
		try:
			value = float(value)
		except:
			return
		self._selectedObj.setScale(value/100, axis, self.rotationLock)
		self.updateProfileToControls()
		# self._scene.pushFree()
		self._selectObject(self._selectedObj)
		self.sceneUpdated()

	def OnScaleEntryMM(self, value, axis):
		if self._selectedObj is None:
			return
		try:
			value = float(value)
		except:
			return
		self._selectedObj.setSize(value, axis, self.rotationLock)
		self.updateProfileToControls()
		# self._scene.pushFree()
		self._selectObject(self._selectedObj)
		self.sceneUpdated()

	def OnDeleteAll(self, e):
		dial = wx.MessageDialog(None, 'Starting a new project will clear the print bed.\nWould you like to continue?', 'New Project', wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
		result = dial.ShowModal() == wx.ID_YES
		if result:
			busyInfo = wx.BusyInfo(_("working... please wait..."), self)
			while len(self._scene.objects()) > 0:
				self._deleteObject(self._scene.objects()[0])
			self._yaw = 1054
			self._pitch = 68
			self._animView = openglGui.animation(self, self._viewTarget.copy(), numpy.array([0,0,90], numpy.float32), 1)
			self._animZoom = openglGui.animation(self, self._zoom, 478, 0.5)
			self.cameraMode = 'default'
			self.setModelView(1)
			return True
		else:
			return False
	def deleteSelection(self, e):
		if self._selectedObj is not None:
			self._deleteObject(self._selectedObj)
			self.QueueRefresh()

	def cameraTop(self,e):
		self._yaw = 0
		self._pitch = 75
		self._zoom = 800
		self._viewTarget[0] = -4
		self._viewTarget[1] = 315
	def cameraSide(self,e):
		self._yaw = -90
		self._pitch = 77
		self._zoom = 910
		self._viewTarget[0] = -393
		self._viewTarget[1] = 1
	def cameraFront(self,e):
		self._yaw = 0
		self._pitch = 0
		self._zoom = 550
		self._viewTarget[0] = -2
		self._viewTarget[1] = -2
	def cameraDefault(self,e):
		self._yaw = -20
		self._pitch = 67
		self._zoom = 667
		self._viewTarget[0] = -75
		self._viewTarget[1] = 204


	def cameraChange(self):
		if self.cameraMode == 'default':
			self._yaw = 0
			self._pitch = 75
			self._zoom = 800
			self._viewTarget[0] = -4
			self._viewTarget[1] = 315
			self._viewTarget[2] = 0
			self.cameraMode = 'front'
		elif self.cameraMode == 'front':
			self._yaw = 0
			self._pitch = 0
			self._zoom = 550
			self._viewTarget[0] = -2
			self._viewTarget[1] = -2
			self._viewTarget[2] = 0
			self.cameraMode = 'top'
		elif self.cameraMode == 'top':
			self._yaw = -90
			self._pitch = 77
			self._zoom = 910
			self._viewTarget[0] = -393
			self._viewTarget[1] = 1
			self._viewTarget[2] = 0
			self.cameraMode = 'right'
		else:
			self._yaw = 1054
			self._pitch = 68
			self._zoom = 478
			self._viewTarget[0] = 0
			self._viewTarget[1] = 0
			self._viewTarget[2] = 90
			self.cameraMode = 'default'
		self.sceneUpdated()

	def OnMenuMultiply(self, e):
		if self._focusObj is None:
			return
		self.OnMultiply(self._focusObj)
	def OnButtonMultiply(self, e):
		if self._selectedObj is None:
			return
		self.OnMultiply(self._selectedObj)

	def OnMultiply(self, obj):
		dlg = wx.NumberEntryDialog(self, _("How many additional copies do you want?"), _("Copies"), _("Duplicate"), 1, 1, 100)
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return

		cnt = dlg.GetValue()

		if cnt> 100:
			#TODO: do it.
			return
		elif cnt > 20:
			dial = wx.MessageDialog(None, "Warning! You are trying to create a large number of duplicates\nwhich may crash the application.\nWould you like to continue anyway?", 'Warning: High number of duplicates', wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
			result = dial.ShowModal() == wx.ID_YES
			if not result:
				return

		busyInfo = wx.BusyInfo(_("working... please wait..."), self)
		dlg.Destroy()
		n = 0
		while True:
			n += 1
			newObj = obj.copy()
			self._scene.add(newObj)
			self.list.append(newObj)
			self._scene.centerAll()
			#if not self._scene.checkPlatform(newObj):
			#	break
			if n > cnt:
				break
		#if n <= cnt:
		#	self.notification.message("Could not create more then %d items" % (n - 1))
		self._scene.remove(newObj)
		self._scene.centerAll()
		self.sceneUpdated()

	def OnSplitObject(self, e):
		if self._focusObj is None:
			return
		self._scene.remove(self._focusObj)
		for obj in self._focusObj.split(self._splitCallback):
			if numpy.max(obj.getSize()) > 2.0:
				self._scene.add(obj)
				self.list.append(obj)
		self._scene.centerAll()
		self._selectObject(None)
		self.sceneUpdated()
	def OnCenter(self, e):
		if self._selectedObj is None:
			return
		self._selectedObj.setPosition(numpy.array([0.0, 0.0]))
		self._scene.pushFree()
		newViewPos = numpy.array([self._selectedObj.getPosition()[0], self._selectedObj.getPosition()[1], self._selectedObj.getSize()[2] / 2])
		self._animView = openglGui.animation(self, self._viewTarget.copy(), newViewPos, 0.5)
		self.sceneUpdated()
	def _splitCallback(self, progress):
		print progress

	def OnMergeObjects(self, e):
		if self._selectedObj is None or self._focusObj is None or self._selectedObj == self._focusObj:
			print "could not merge"
			return
		self._scene.merge(self._selectedObj, self._focusObj)
		self.sceneUpdated()

	def sceneUpdated(self):
		# self._sceneUpdateTimer.Start(500, True)
		#self._slicer.abortSlicer()
		self._scene.setSizeOffsets(numpy.array(profile.calculateObjectSizeOffsets(), numpy.float32))
		self.QueueRefresh()

	def _onRunSlicer(self, e):
		#if self._isSimpleMode:
		#	self.GetTopLevelParent().simpleSettingsPanel.setupSlice()
		#self._slicer.runSlicer(self._scene)
		if self._isSimpleMode:
			profile.resetTempOverride()

	def _updateSliceProgress(self, progressValue, ready):
		# if not ready:
		# 	if self.printButton.getProgressBar() is not None and progressValue >= 0.0 and abs(self.printButton.getProgressBar() - progressValue) < 0.01:
		# 		return
		# self.printButton.setDisabled(not ready)
		# if progressValue >= 0.0:
		# 	self.printButton.setProgressBar(progressValue)
		# else:
		# 	self.printButton.setProgressBar(None)
		print progressValue
		if self._gcode is not None:
			self._gcode = None
			for layerVBOlist in self._gcodeVBOs:
				for vbo in layerVBOlist:
					self.glReleaseList.append(vbo)
			self._gcodeVBOs = []
		if ready:
			# self.printButton.setProgressBar(None)
			cost = self._slicer.getFilamentCost()
			# if cost is not None:
			# 	self.printButton.setBottomText('%s\n%s\n%s' % (self._slicer.getPrintTime(), self._slicer.getFilamentAmount(), cost))
			# else:
			# 	self.printButton.setBottomText('%s\n%s' % (self._slicer.getPrintTime(), self._slicer.getFilamentAmount()))
			self._gcode = gcodeInterpreter.gcode()
			self._gcodeFilename = self._slicer.getGCodeFilename()
		# else:
		# 	self.printButton.setBottomText('')
		self.QueueRefresh()
	def _updateEngineProgress(self, progressValue):
		progress = int(progressValue * 100)
		if progress > 0:
			self.sliceButton.setTooltipText("Slicing...%d%%" % progress)
		result = self._engine.getResult()
		finished = result is not None and result.isFinished()
		self.sliceButton.setProgressBar(progressValue)
		# if not finished:
			# if self.printButton.getProgressBar() is not None and progressValue >= 0.0 and abs(self.printButton.getProgressBar() - progressValue) < 0.01:
			# 	return
		# self.printButton.setDisabled(not finished)
		# if progressValue >= 0.0:
		# 	self.printButton.setProgressBar(progressValue)
		# else:
		# 	self.printButton.setProgressBar(None)
		self.QueueRefresh()
		#self._engineResultView.setResult(result)
		if finished:
			self.sliceButton.setProgressBar(None)
			timeText = '%s' % (result.getPrintTime())
			weightTextGrams = '%.0f' % (result.getFilamentWeight()*1000)

			time = timeText.split(':')

			hours = time[0]
			minutes = time[1]

			self.timeEstLabelTime.setTooltipText("%sh:%sm" % (hours, minutes))
			self.weightLabelGrams.setTooltipText("%sg" % (weightTextGrams))

			self.OnSliceDone(result._gcodeData)
			self.abortButton.setHidden(True)
			self.sliceButton.setHidden(False)
			# for e in xrange(0, int(profile.getMachineSetting('extruder_amount'))):
			# 	amount = result.getFilamentAmount(e)
			# 	if amount is None:
			# 		continue
			# 	text += '\n%s' % (amount)
			# 	cost = result.getFilamentCost(e)
			# 	if cost is not None:
			# 		text += '\n%s' % (cost)
			#self.printButton.setBottomText(text)

		self.QueueRefresh()

	def _loadGCode(self):
		self._gcode.progressCallback = self._gcodeLoadCallback
		self._gcode.load(self._gcodeFilename)

	def _gcodeLoadCallback(self, progress):
		if self._gcode is None:
			return True
		if len(self._gcode.layerList) % 15 == 0:
			time.sleep(0.1)
		if self._gcode is None:
			return True
		self.layerSelect.setRange(1, len(self._gcode.layerList) - 1)
		if self.viewMode == 'gcode':
			self._queueRefresh()
		self.Refresh()
		return False

	def loadScene(self, fileList):
		self.busyInfo = wx.BusyInfo(_("loading model... please wait..."), self)
		for filename in fileList:
			try:
				objList = meshLoader.loadMeshes(filename)
			except MemoryError:
				traceback.print_exc()
				dial = wx.MessageDialog(None, "The model could not be imported because it is too large. Try reducing the number of polygons/triangles and importing again.", "Error encountered during Model Import", wx.OK|wx.ICON_EXCLAMATION)
				dial.ShowModal()
				dial.Destroy()
				self.busyInfo = None
			except IOError:
				traceback.print_exc()
				dial = wx.MessageDialog(None, "File was not found. Please check if your file exists and try again!", "Error encountered during Model Import", wx.OK|wx.ICON_EXCLAMATION)
				dial.ShowModal()
				dial.Destroy()
			else:
				self.busyInfo = None
				for obj in objList:
					if self._objectLoadShader is not None:
						obj._loadAnim = openglGui.animation(self, 0, 0, 0.1) #j
					else:
						obj._loadAnim = None
					self._scene.add(obj)
					#stl.saveAsSTL(obj._meshList[0], filename)
					#print obj._meshList[0]
					item = ProjectObject(self, filename)
					self.list.append(item)
					self._scene.centerAll()
					self._selectObject(obj)
					profile.putPreference('selectedFile', obj.getName())
					#print obj
		self.sceneUpdated()

	def _deleteObject(self, obj):
		if obj == self._selectedObj:
			self._selectObject(None)
		if obj == self._focusObj:
			self._focusObj = None
		self._scene.remove(obj)
		for m in obj._meshList:
			if m.vbo is not None and m.vbo.decRef():
				self.glReleaseList.append(m.vbo)
		import gc
		gc.collect()
		self.sceneUpdated()

	def _selectObject(self, obj, zoom = True):
		if obj != self._selectedObj:
			self._selectedObj = obj
			self.updateProfileToControls()
			self.updateToolButtons()

		if zoom and obj is not None:
			newViewPos = numpy.array([obj.getPosition()[0], obj.getPosition()[1], obj.getMaximum()[2] / 2])
			self._animView = openglGui.animation(self, self._viewTarget.copy(), newViewPos, 0.5)
			newZoom = obj.getBoundaryCircle() * 6
			if newZoom > numpy.max(self._machineSize) * 3:
				newZoom = numpy.max(self._machineSize) * 3
			self._animZoom = openglGui.animation(self, self._zoom, newZoom, 0.5)
	def updateScaleForm(self, x, y, z, scaleX, scaleY, scaleZ, axis):
		if self._selectedObj is not None:
			#scale = self._selectedObj.getScale()
			#size = self._selectedObj.getSize()
			#str(int(round(float(scale[0])*100)))
			self.scaleXmmctrl.setValue(round(x, 1))
			self.scaleYmmctrl.setValue(round(y, 1))
			self.scaleZmmctrl.setValue(round(z, 1))


			if axis == "X":
				self.scaleXctrl.setValue(int(round(float(scaleX)*100)))
			# elif axis == "Y":
			# 	self.scaleYctrl.setValue(int(round(float(scaleY)*100)))
			# elif axis == "Z":
			# 	self.scaleZctrl.setValue(int(round(float(scaleZ)*100)))
			elif axis == "XYZ":
				self.scaleXctrl.setValue(int(round(float(scaleX)*100)))
				# self.scaleYctrl.setValue(int(round(float(scaleY)*100)))
				# self.scaleZctrl.setValue(int(round(float(scaleZ)*100)))

	def updateProfileToControls(self):
		oldSimpleMode = self._isSimpleMode
		self._isSimpleMode = profile.getPreference('startMode') == 'Simple'
		if self._isSimpleMode and not oldSimpleMode:
			self._scene.arrangeAll()
			self.sceneUpdated()
		self._machineSize = numpy.array([profile.getPreferenceFloat('machine_width'), profile.getPreferenceFloat('machine_depth'), profile.getPreferenceFloat('machine_height')])
		self._objColors[0] = profile.getPreferenceColour('model_colour')
		self._objColors[1] = profile.getPreferenceColour('model_colour2')
		self._objColors[2] = profile.getPreferenceColour('model_colour3')
		self._objColors[3] = profile.getPreferenceColour('model_colour4')
		self._scene.setMachineSize(self._machineSize)
		self._scene.setSizeOffsets(numpy.array(profile.calculateObjectSizeOffsets(), numpy.float32))
		self._scene.setHeadSize(profile.getPreferenceFloat('extruder_head_size_min_x'), profile.getPreferenceFloat('extruder_head_size_max_x'), profile.getPreferenceFloat('extruder_head_size_min_y'), profile.getPreferenceFloat('extruder_head_size_max_y'), profile.getPreferenceFloat('extruder_head_size_height'))

		if self._selectedObj is not None:
			scale = self._selectedObj.getScale()
			size = self._selectedObj.getSize()
			#str(int(round(float(scale[0])*100)))

			self.scaleXctrl.setValue(int(round(float(scale[0])*100)))
			# self.scaleYctrl.setValue(int(round(float(scale[1])*100)))
			# self.scaleZctrl.setValue(int(round(float(scale[2])*100)))
			self.scaleXmmctrl.setValue(round(size[0], 1))
			self.scaleYmmctrl.setValue(round(size[1], 1))
			self.scaleZmmctrl.setValue(round(size[2], 1))
	def updateButtonLabels(self):
		infillText = profile.getProfileSettingFloat('fill_density')
		self.infillMenuButton.setTooltipText(str(infillText))

	def resetSlicingSettings(self):
		self.medResolution(None)
		self.setInfill(self.SPARSE_INFILL_VALUE, "Sparse")
		self.setWallThickness(2)
		self.supportOff(None)
		self.setFilament(1.75)
		self.setPrintSpeed(70)
		self.setTemperature(220)

	def OnKeyChar(self, keyCode):
		if keyCode == 310 and version.isDevVersion():
			self.setModelView(4)
		if keyCode == wx.WXK_DELETE or keyCode == wx.WXK_NUMPAD_DELETE:
			if self._selectedObj is not None:
				self._deleteObject(self._selectedObj)
				self.QueueRefresh()
		if keyCode == wx.WXK_UP:
			self.layerSelect.setValue(self.layerSelect.getValue() + 1)
			self.QueueRefresh()

			if len(self._konamCode) == 0:
				self._konamCode.append("U")
			elif len(self._konamCode) == 1:
				self._konamCode.append("U")
			else:
				self._konamCode = []

		elif keyCode == wx.WXK_DOWN:
			self.layerSelect.setValue(self.layerSelect.getValue() - 1)
			self.QueueRefresh()

			if len(self._konamCode) == 2:
				self._konamCode.append("D")
			elif len(self._konamCode) == 3:
				self._konamCode.append("D")
			else:
				self._konamCode = []

		elif keyCode == wx.WXK_LEFT:
			self.layerSelect.setValue(self.layerSelect.getValue() - 1)
			self.QueueRefresh()
			if len(self._konamCode) == 4:
				self._konamCode.append("L")
			elif len(self._konamCode) == 6:
				self._konamCode.append("L")
			else:
				self._konamCode = []
		elif keyCode == wx.WXK_RIGHT:
			self.layerSelect.setValue(self.layerSelect.getValue() + 1)
			self.QueueRefresh()
			if len(self._konamCode) == 5:
				self._konamCode.append("R")
			elif len(self._konamCode) == 7:
				self._konamCode.append("R")
			else:
				self._konamCode = []

		elif keyCode == 98:
			if len(self._konamCode) == 8:
				self._konamCode.append("B")
			else:
				self._konamCode = []
		elif keyCode == 97:
			if len(self._konamCode) == 9:
				self._konamCode.append("A")
			else:
				self._konamCode = []
		elif keyCode == wx.WXK_RETURN:
			if len(self._konamCode) == 10:
				print self._konamCode
				self._konamCode = []
				ecw = expertConfig.expertConfigWindow(self)
				ecw.Centre()
				ecw.Show(True)
				return

		elif keyCode == wx.WXK_PAGEUP:
			self.layerSelect.setValue(self.layerSelect.getValue() + 10)
			self.QueueRefresh()
		elif keyCode == wx.WXK_PAGEDOWN:
			self.layerSelect.setValue(self.layerSelect.getValue() - 10)
			self.QueueRefresh()


		if keyCode == wx.WXK_F3 and wx.GetKeyState(wx.WXK_SHIFT):
			shaderEditor(self, self.ShaderUpdate, self._objectLoadShader.getVertexShader(), self._objectLoadShader.getFragmentShader())
		if keyCode == wx.WXK_F4 and wx.GetKeyState(wx.WXK_SHIFT):
			from collections import defaultdict
			from gc import get_objects
			self._beforeLeakTest = defaultdict(int)
			for i in get_objects():
				self._beforeLeakTest[type(i)] += 1
		if keyCode == wx.WXK_F5 and wx.GetKeyState(wx.WXK_SHIFT):
			from collections import defaultdict
			from gc import get_objects
			self._afterLeakTest = defaultdict(int)
			for i in get_objects():
				self._afterLeakTest[type(i)] += 1
			for k in self._afterLeakTest:
				if self._afterLeakTest[k]-self._beforeLeakTest[k]:
					print k, self._afterLeakTest[k], self._beforeLeakTest[k], self._afterLeakTest[k] - self._beforeLeakTest[k]
		if keyCode == wx.WXK_SPACE:
			self._konamCode = []
			self.cameraChange()
		if keyCode == wx.WXK_ESCAPE:
			self._selectedObj = None
			self._focus = None
			self.sceneUpdated()
	def ShaderUpdate(self, v, f):
		s = opengl.GLShader(v, f)
		if s.isValid():
			self._objectLoadShader.release()
			self._objectLoadShader = s
			for obj in self._scene.objects():
				obj._loadAnim = openglGui.animation(self, 1, 0, 1.5)
			self.QueueRefresh()

	def OnMouseDown(self,e):
		#for b in self.supportLines:
		#	print b
		#print self.supportLines
		self._mouseX = e.GetX()
		self._mouseY = e.GetY()
		self._mouseClick3DPos = self._mouse3Dpos
		self._mouseClickFocus = self._focusObj
		#print self._mouseClick3DPos
		#self.xText.setTooltip("X: " + str(self._mouseClick3DPos[0]))
		#self.yText.setTooltip("Y: " + str(self._mouseClick3DPos[1]))
		#self.zText.setTooltip("Z: " + str(self._mouseClick3DPos[2]))
		###self._mouseClick3DPos
		#p = glReadPixels(self._mouseX, self._mouseY, 1, 1, GL_RGBA, GL_UNSIGNED_INT_8_8_8_8)[0][0] >> 8

		if e.ButtonDClick():
			self._mouseState = 'doubleClick'
		else:
			self._mouseState = 'dragOrClick'

		p0, p1 = self.getMouseRay(self._mouseX, self._mouseY)
		p0 -= self.getObjectCenterPos() - self._viewTarget
		p1 -= self.getObjectCenterPos() - self._viewTarget
		if self.tool.OnDragStart(p0, p1):
			self._mouseState = 'tool'
		if self.tool2.OnDragStart(p0, p1):
			self._mouseState = 'tool'

		if self._mouseState == 'dragOrClick':
			if e.GetButton() == 1:
				for element in self.topmenuGroup:
					element.setSelected(False)
				if self._focusObj is not None:
					self._selectObject(self._focusObj, False)
					profile.putPreference('selectedFile', self._selectedObj._name)
					self.QueueRefresh()
				else:
					profile.putPreference('selectedFile', '')
					self._selectedObj = None
					self._focus = None

	def testCollision(self, mouseX, mouseY, x1, y1, x2, y2, z):
		#given a line, create a rectangle (with a thickness of x) and see if the mouse pos collides with it!
		#for s in self.supportLines:
		currentZ = self.layerSelect.getValue()
		z = int(round(z/0.3)) #TODO. hahaha this doesn't work.
		if currentZ != z+1:
			pass
			#return False
		#print currentZ
		#print z
		#	x1 = s[0][0]
		#	y1 = s[0][1]
		#	x2 = s[1][0]
		#	y2 = s[1][1]
		if x1 < x2:
			x1 -= 0.3
			x2 += 0.3
		else:
			x1 += 0.3
			x2 -= 0.3

		if y1 < y2:
			y1 -= 0.3
			y2 += 0.3
		else:
			y1 += 0.3
			y2 -= 0.3
		betweenX = False
		betweenY = False

		if x1 > mouseX > x2 or x1 < mouseX < x2:
			betweenX = True
		if y1 > mouseY > y2 or y1 < mouseY < y2:
			betweenY = True

		if x1 == x2 and y1 == y2:
			print "yeah"
			#return True


		#if x1 > mouseX > x2 and y1 > mouseY > y2 or x1 < mouseX < x2 and y1 > mouseY > y2:
		if betweenX and betweenY:
			return True
		else:
			return False

	#	if x1-0.3 < mouseX < x2+0.3 and y1-0.3 < mouseY < y2+0.3 or x1+0.3 > mouseX > x2-0.3 and y1-0.3 < mouseY < y2+0.3:
		#	return True
		#else:
		#	return False

	def OnMouseUp(self, e):
		if e.LeftIsDown() or e.MiddleIsDown() or e.RightIsDown():
			return
		if self._mouseState == 'dragOrClick':
			if e.GetButton() == 1:
				self._selectObject(self._focusObj)
				self.sceneUpdated()
			if e.GetButton() == 3:

					menu = wx.Menu()
					if self._focusObj is not None:
						self.Bind(wx.EVT_MENU, lambda e: self._deleteObject(self._focusObj), menu.Append(-1, _('Delete')))
						self.Bind(wx.EVT_MENU, self.OnMenuMultiply, menu.Append(-1, _('Duplicate')))
						self.Bind(wx.EVT_MENU, self.OnCenter, menu.Append(-1, _('Center on platform')))
						if version.isDevVersion():
							self.Bind(wx.EVT_MENU, self.OnSplitObject, menu.Append(-1, _('Split')))
					if self._selectedObj != self._focusObj and self._focusObj is not None and int(profile.getPreference('extruder_amount')) > 1:
						self.Bind(wx.EVT_MENU, self.OnMergeObjects, menu.Append(-1, 'Dual extrusion merge'))
					if len(self._scene.objects()) > 0:
						self.Bind(wx.EVT_MENU, self.OnDeleteAll, menu.Append(-1, _('New Project')))
					if menu.MenuItemCount > 0:
						self.PopupMenu(menu)
					menu.Destroy()
		elif self._mouseState == 'dragObject' and self._selectedObj is not None:
			# if not version.isDevVersion():
			#self._scene.pushFree()
			self.sceneUpdated()
		elif self._mouseState == 'tool':
			busyInfo = wx.BusyInfo(_("working... please wait..."), self)
			if self.tempMatrix is not None and self._selectedObj is not None:
				self._selectedObj.applyMatrix(self.tempMatrix)
				#self._scene.pushFree()
				self._selectObject(self._selectedObj)
			self.tempMatrix = None
			self.tool.OnDragEnd()
			self.tool2.OnDragEnd()
			self.sceneUpdated()
			self.updateProfileToControls()
		self._mouseState = None

	def OnMouseMotion(self,e):
		p0, p1 = self.getMouseRay(e.GetX(), e.GetY())
		p0 -= self.getObjectCenterPos() - self._viewTarget
		p1 -= self.getObjectCenterPos() - self._viewTarget

		if e.Dragging() and self._mouseState is not None:
			if self._mouseState == 'tool':
				self.tool.OnDrag(p0, p1)
				self.tool2.OnDrag(p0, p1)
			elif not e.LeftIsDown() and not e.RightIsDown() and e.MiddleIsDown():
					a = math.cos(math.radians(self._yaw)) / 3.0
					b = math.sin(math.radians(self._yaw)) / 3.0
					self._viewTarget[0] += float(e.GetX() - self._mouseX) * -a
					self._viewTarget[1] += float(e.GetX() - self._mouseX) * b
					self._viewTarget[0] += float(e.GetY() - self._mouseY) * b
					self._viewTarget[1] += float(e.GetY() - self._mouseY) * a
					#print self._viewTarget[0]
					#print self._viewTarget[1]
					#print "-----------------"
			elif not e.LeftIsDown() and e.RightIsDown():
				self._mouseState = 'drag'
				if wx.GetKeyState(wx.WXK_SHIFT):
					a = math.cos(math.radians(self._yaw)) / 3.0
					b = math.sin(math.radians(self._yaw)) / 3.0
					self._viewTarget[0] += float(e.GetX() - self._mouseX) * -a
					self._viewTarget[1] += float(e.GetX() - self._mouseX) * b
					self._viewTarget[0] += float(e.GetY() - self._mouseY) * b
					self._viewTarget[1] += float(e.GetY() - self._mouseY) * a
				else:
					self._yaw += e.GetX() - self._mouseX
					self._pitch -= e.GetY() - self._mouseY
				if self._pitch > 180:
					self._pitch = 180
				if self._pitch < 0:
					self._pitch = 0
			#elif (e.LeftIsDown() and e.RightIsDown()) or e.MiddleIsDown():
			elif (e.LeftIsDown() and e.RightIsDown()):
				self._mouseState = 'drag'
				self._zoom += e.GetY() - self._mouseY
				if self._zoom < 1:
					self._zoom = 1
				if self._zoom > numpy.max(self._machineSize) * 3:
					self._zoom = numpy.max(self._machineSize) * 3
			elif e.LeftIsDown() and self._selectedObj is not None and self._selectedObj == self._mouseClickFocus:
				self._mouseState = 'dragObject'
				z = max(0, self._mouseClick3DPos[2])
				p0, p1 = self.getMouseRay(self._mouseX, self._mouseY)
				p2, p3 = self.getMouseRay(e.GetX(), e.GetY())
				p0[2] -= z
				p1[2] -= z
				p2[2] -= z
				p3[2] -= z
				cursorZ0 = p0 - (p1 - p0) * (p0[2] / (p1[2] - p0[2]))
				cursorZ1 = p2 - (p3 - p2) * (p2[2] / (p3[2] - p2[2]))
				diff = cursorZ1 - cursorZ0
				self._selectedObj.setPosition(self._selectedObj.getPosition() + diff[0:2])

		if not e.Dragging() or self._mouseState != 'tool':
			self.tool.OnMouseMove(p0, p1)
			self.tool2.OnMouseMove(p0, p1)

		self._mouseX = e.GetX()
		self._mouseY = e.GetY()

	def OnMouseWheel(self, e):
		if wx.GetKeyState(wx.WXK_SHIFT):
			delta = float(e.GetWheelRotation()) / float(e.GetWheelDelta())
			delta = max(min(delta,1),-1)
			self.layerSelect.setValue(int(self.layerSelect.getValue() + delta))
			self.Refresh()
			return

		delta = float(e.GetWheelRotation()) / float(e.GetWheelDelta())
		delta = max(min(delta,4),-4)
		self._zoom *= 1.0 - delta / 10.0
		if self._zoom < 1.0:
			self._zoom = 1.0
		if self._zoom > numpy.max(self._machineSize) * 4:
			self._zoom = numpy.max(self._machineSize) * 4
		self.Refresh()

	def OnMouseLeave(self, e):
		self._mouseX = -1

	def getMouseRay(self, x, y):
		if self._viewport is None:
			return numpy.array([0,0,0],numpy.float32), numpy.array([0,0,1],numpy.float32)
		p0 = opengl.unproject(x, self._viewport[1] + self._viewport[3] - y, 0, self._modelMatrix, self._projMatrix, self._viewport)
		p1 = opengl.unproject(x, self._viewport[1] + self._viewport[3] - y, 1, self._modelMatrix, self._projMatrix, self._viewport)
		p0 -= self._viewTarget
		p1 -= self._viewTarget
		return p0, p1

	def _init3DView(self):
		# set viewing projection
		size = self.GetSize()
		glViewport(0, 0, size.GetWidth(), size.GetHeight())
		glLoadIdentity()

		glLightfv(GL_LIGHT0, GL_POSITION, [0.2, 0.2, 1.0, 0.0])

		glDisable(GL_RESCALE_NORMAL)
		glDisable(GL_LIGHTING)
		glDisable(GL_LIGHT0)
		glEnable(GL_DEPTH_TEST)
		glDisable(GL_CULL_FACE)
		glDisable(GL_BLEND)
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

		glClearColor(1, 1, 1, 1.0)
		glClearStencil(0)
		glClearDepth(1.0)

		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		aspect = float(size.GetWidth()) / float(size.GetHeight())
		gluPerspective(45.0, aspect, 1.0, numpy.max(self._machineSize) * 4)

		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

	def OnPaint(self,e):
		#if machineCom.machineIsConnected():
		#	self.printButton._imageID = 6
		#	self.printButton._tooltip = 'Print'

		if len(removableStorage.getPossibleSDcardDrives()) > 0:
			#self.printButton._imageID = 2
				drives = removableStorage.getPossibleSDcardDrives()
				#if len(drives) > 1:
				#	dlg = wx.SingleChoiceDialog(self, "Select SD drive", "Multiple removable drives have been found,\nplease select your SD card drive", map(lambda n: n[0], drives))
				#	if dlg.ShowModal() != wx.ID_OK:
				#		dlg.Destroy()
				#		return
				#	drive = drives[dlg.GetSelection()]
				#	dlg.Destroy()
				#else:
				drive = drives[0]
				if str(drive[1]) != str(profile.getPreference('sdpath')):
					#print drive
					#print profile.getPreference('sdpath')
					profile.putPreference('sdpath', drive[1])
		# else:
			# self.printButton._imageID = 26
			#self.printButton._tooltip = 'Save toolpath'
		if len(removableStorage.getPossibleSDcardDrives()) == 0:
			#profile.putPreference('sdpath', '')
			self.ejectSDButton._hidden = True
			self.saveToSdCardButton._disabled = True

		elif len(removableStorage.getPossibleSDcardDrives()) > 0 and self.modalAfterSave._hidden == False and self.savedIcon._imageID == 21 and not self.savedText2._tooltipText._text == self.ejectedMessage:
			self.ejectSDButton._hidden = False

		else:
			self.ejectSDButton._hidden = True
			self.saveToSdCardButton._disabled = True

		if len(removableStorage.getPossibleSDcardDrives()) > 0:
			self.saveToSdCardButton._disabled = False
			self.saveToSdCardButtonOverlay._hidden = True
		elif self.modalTest._hidden == False:
			self.saveToSdCardButtonOverlay._hidden = False

		if not self._isSlicing and self.getProgressBar() is not None:
			self.setProgressBar(None)

		if self._animView is not None:
			self._viewTarget = self._animView.getPosition()
			if self._animView.isDone():
				self._animView = None
		if self._animZoom is not None:
			self._zoom = self._animZoom.getPosition()
			if self._animZoom.isDone():
				self._animZoom = None
		if self.viewMode == 'gcode' and self._gcode is not None:
			try:
				self._viewTarget[2] = self._gcode.layerList[self.layerSelect.getValue()][-1]['points'][0][2]
			except:
				pass
		if self._objectShader is None:
			if opengl.hasShaderSupport():
				self._objectShader = opengl.GLShader("""
varying float light_amount;

void main(void)
{
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
    gl_FrontColor = gl_Color;

	light_amount = abs(dot(normalize(gl_NormalMatrix * gl_Normal), normalize(gl_LightSource[0].position.xyz)));
	light_amount += 0.2;
}
				""","""
varying float light_amount;

void main(void)
{
	gl_FragColor = vec4(gl_Color.xyz * light_amount, gl_Color[3]);
}
				""")
				self._objectOverhangShader = opengl.GLShader("""
uniform float cosAngle;
uniform mat3 rotMatrix;
varying float light_amount;

void main(void)
{
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
    gl_FrontColor = gl_Color;

	light_amount = abs(dot(normalize(gl_NormalMatrix * gl_Normal), normalize(gl_LightSource[0].position.xyz)));
	light_amount += 0.2;
	if (normalize(rotMatrix * gl_Normal).z < -cosAngle)
	{
		light_amount = -10.0;
	}
}
				""","""
varying float light_amount;

void main(void)
{
	if (light_amount == -10.0)
	{
		gl_FragColor = vec4(1.0, 0.65, 0.01, gl_Color[3]);
	}else{
		gl_FragColor = vec4(gl_Color.xyz * light_amount, gl_Color[3]);
	}
}
				""")
				self._objectLoadShader = opengl.GLShader("""
uniform float intensity;
uniform float scale;
varying float light_amount;

void main(void)
{
	vec4 tmp = gl_Vertex;
    tmp.x += sin(tmp.z/5.0+intensity*30.0) * scale * intensity;
    tmp.y += sin(tmp.z/3.0+intensity*40.0) * scale * intensity;
    gl_Position = gl_ModelViewProjectionMatrix * tmp;
    gl_FrontColor = gl_Color;

	light_amount = abs(dot(normalize(gl_NormalMatrix * gl_Normal), normalize(gl_LightSource[0].position.xyz)));
	light_amount += 0.2;
}
			""","""
uniform float intensity;
varying float light_amount;

void main(void)
{
	gl_FragColor = vec4(gl_Color.xyz * light_amount, 1.0-intensity);
}
				""")
			if self._objectShader == None or not self._objectShader.isValid():
				self._objectShader = opengl.GLFakeShader()
				self._objectOverhangShader = opengl.GLFakeShader()
				self._objectLoadShader = None
		self._init3DView()

		glTranslate(0,0,-self._zoom)
		glRotate(-self._pitch, 1,0,0)
		glRotate(self._yaw, 0,0,1)
		glTranslate(-self._viewTarget[0],-self._viewTarget[1],-self._viewTarget[2])

		self._viewport = glGetIntegerv(GL_VIEWPORT)
		self._modelMatrix = glGetDoublev(GL_MODELVIEW_MATRIX)
		self._projMatrix = glGetDoublev(GL_PROJECTION_MATRIX)

		glClearColor(1,1,1,1)
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

		if self.viewMode != 'gcode':
			for n in xrange(0, len(self._scene.objects())):
				obj = self._scene.objects()[n]
				glColor4ub((n >> 16) & 0xFF, (n >> 8) & 0xFF, (n >> 0) & 0xFF, 0xFF)
				self._renderObject(obj)

		if self._mouseX > -1:
			glFlush()
			n = glReadPixels(self._mouseX, self.GetSize().GetHeight() - 1 - self._mouseY, 1, 1, GL_RGBA, GL_UNSIGNED_INT_8_8_8_8)[0][0] >> 8
			if n < len(self._scene.objects()):
				self._focusObj = self._scene.objects()[n]
			else:
				self._focusObj = None
			f = glReadPixels(self._mouseX, self.GetSize().GetHeight() - 1 - self._mouseY, 1, 1, GL_DEPTH_COMPONENT, GL_FLOAT)[0][0]
			#self.GetTopLevelParent().SetTitle(hex(n) + " " + str(f))
			self._mouse3Dpos = opengl.unproject(self._mouseX, self._viewport[1] + self._viewport[3] - self._mouseY, f, self._modelMatrix, self._projMatrix, self._viewport)
			self._mouse3Dpos -= self._viewTarget

		self._init3DView()
		glTranslate(0,0,-self._zoom)
		glRotate(-self._pitch, 1,0,0)
		glRotate(self._yaw, 0,0,1)
		glTranslate(-self._viewTarget[0],-self._viewTarget[1],-self._viewTarget[2])

		if self.viewMode == 'gcode':
			if self._gcode is not None and self._gcode.layerList is None:
				self._gcodeLoadThread = threading.Thread(target=self._loadGCode)
				self._gcodeLoadThread.daemon = True
				self._gcodeLoadThread.start()
			if self._gcode is not None and self._gcode.layerList is not None:
				glPushMatrix()
				glTranslate(-self._machineSize[0] / 2, -self._machineSize[1] / 2, 0)
				t = time.time()
				drawUpTill = min(len(self._gcode.layerList), self.layerSelect.getValue() + 1)
				switch = False
				for n in xrange(0, drawUpTill):
					c = 1.0 - float(drawUpTill - n) / 15
					c = max(0.3, c)

					if len(self._gcodeVBOs) < n + 1:
						self._counter+=1
						self._gcodeVBOs.append(self._generateGCodeVBOs(self._gcode.layerList[n]))
						if time.time() - t > 0.5:
							self.QueueRefresh()
							break
					###['WALL-OUTER', 'WALL-INNER', 'FILL', 'SUPPORT', 'SKIRT', selected support]

					if n in self._pauses:
						if switch:
							switch = False
						else:
							switch = True
					if switch:
						switchPerimeterColour = 140, 50, 63
						switchInfillColour = 140, 50, 63
						switchLoopsColour = 140, 50, 63
					else:
						switchPerimeterColour = 140, 198, 63
						switchInfillColour = 251, 176, 59
						switchLoopsColour = 57, 181, 74
					if n == drawUpTill - 1: #current layer
						#print len(self._gcodeVBOs[n])
						if len(self._gcodeVBOs[n]) < 11:
							self._gcodeVBOs[n] += self._generateGCodeVBOs2(self._gcode.layerList[n])



						#glColor3ub(140, 198, 63) #perimeter
						glColor3ub(switchPerimeterColour[0], switchPerimeterColour[1], switchPerimeterColour[2]) #perimeter
						self._gcodeVBOs[n][10].render(GL_QUADS)
						glColor3ub(0,0,0)#not sure
						self._gcodeVBOs[n][11].render(GL_QUADS)
						glColor3ub(204,204,204)#not sure
						self._gcodeVBOs[n][12].render(GL_QUADS)
						glColor3ub(255,0,0)#support? don't think so?
						self._gcodeVBOs[n][13].render(GL_QUADS)

						glColor3ub(switchLoopsColour[0], switchLoopsColour[1], switchLoopsColour[2]) #loops
						self._gcodeVBOs[n][14].render(GL_QUADS)
						glColor3ub(switchInfillColour[0], switchInfillColour[1], switchInfillColour[2]) #infill
						self._gcodeVBOs[n][15].render(GL_QUADS)
						self._gcodeVBOs[n][19].render(GL_QUADS)
						glColor3ub(204,204,204) #skirt
						self._gcodeVBOs[n][16].render(GL_QUADS)
						glColor3ub(0, 0, 204)
						self._gcodeVBOs[n][18].render(GL_QUADS)
						glColor3ub(204,204,204)#support
						self._gcodeVBOs[n][17].render(GL_QUADS)


					else: #not current layer
						glColor3ub(switchPerimeterColour[0], switchPerimeterColour[1], switchPerimeterColour[2]) #perimeter
						self._gcodeVBOs[n][0].render(GL_LINES)
						glColor3ub(0, 0, 0) #does nothing
						#self._gcodeVBOs[n][1].render(GL_LINES)
						glColor3ub(0, 0, 0) #does nothing
						#self._gcodeVBOs[n][2].render(GL_LINES)
						glColor3ub(0, 0, 0) #does nothing
						#self._gcodeVBOs[n][3].render(GL_LINES)

						glColor3ub(190, 190, 190) #bridge i think
						self._gcodeVBOs[n][4].render(GL_LINES)


						glColor3ub(255, 226, 183) #infill
						if n > drawUpTill - 10:
							self._gcodeVBOs[n][5].render(GL_LINES)
						self._gcodeVBOs[n][9].render(GL_LINES)


						glColor3ub(204, 204, 204) #skirt
						self._gcodeVBOs[n][6].render(GL_LINES)


						glColor3ub(0, 0, 0) #Support2. doesn't seem to do anything
						#self._gcodeVBOs[n][8].render(GL_LINES)
						glColor3ub(204, 204, 204) #support
						self._gcodeVBOs[n][7].render(GL_LINES)
						#if len(self._gcodeVBOs[n][8]._asdf) != 0:
						#	for x in self._gcodeVBOs[n][8]._asdf:
						#		pass
								#print x
						#for p in self.trimList:
						#	if self._gcodeVBOs[n][6] == p:
						#		glColor3ub(204, 0, 0)


				glPopMatrix()
		else:
			glStencilFunc(GL_ALWAYS, 1, 1)
			glStencilOp(GL_INCR, GL_INCR, GL_INCR)

			if self.viewMode == 'overhang':
				self._objectOverhangShader.bind()
				self._objectOverhangShader.setUniform('cosAngle', math.cos(math.radians(90 - profile.getProfileSettingFloat('support_angle'))))
			else:
				self._objectShader.bind()
			self._anObjectIsOutsidePlatform = True
			for obj in self._scene.objects():
				if obj._loadAnim is not None:
					if obj._loadAnim.isDone():
						obj._loadAnim = None
					else:
						continue


				brightness = 0.7
				if self._focusObj == obj:
					brightness = 0.8
				elif self._focusObj is not None or self._selectedObj is not None and obj != self._selectedObj:
					brightness = 0.7
				if self._selectedObj == obj:
					brightness = 1.0
				if self._selectedObj == obj or self._selectedObj is None:
					#If we want transparent, then first render a solid black model to remove the printer size lines.
					if self.viewMode == 'transparent':
						glColor4f(0, 0, 0, 0)
						self._renderObject(obj)
						glEnable(GL_BLEND)
						glBlendFunc(GL_ONE, GL_ONE)
						glDisable(GL_DEPTH_TEST)
						brightness *= 0.5
					if self.viewMode == 'xray':
						glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
					glStencilOp(GL_INCR, GL_INCR, GL_INCR)
					glEnable(GL_STENCIL_TEST)

				if self.viewMode == 'overhang':
					if self._selectedObj == obj and self.tempMatrix is not None:
						self._objectOverhangShader.setUniform('rotMatrix', obj.getMatrix() * self.tempMatrix)
					else:
						self._objectOverhangShader.setUniform('rotMatrix', obj.getMatrix())

				if not self._scene.checkPlatform(obj):
					glColor4f(0.5 * brightness, 0.5 * brightness, 0.5 * brightness, 0.8 * brightness)
					self._renderObject(obj)
					self._anObjectIsOutsidePlatform = False
				else:
					self._renderObject(obj, brightness)
				glDisable(GL_STENCIL_TEST)
				glDisable(GL_BLEND)
				glEnable(GL_DEPTH_TEST)
				glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)

			if self.viewMode == 'xray':
				glPushMatrix()
				glLoadIdentity()
				glEnable(GL_STENCIL_TEST)
				glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP)
				glDisable(GL_DEPTH_TEST)
				for i in xrange(2, 15, 2):
					glStencilFunc(GL_EQUAL, i, 0xFF)
					glColor(float(i)/10, float(i)/10, float(i)/5)
					glBegin(GL_QUADS)
					glVertex3f(-1000,-1000,-10)
					glVertex3f( 1000,-1000,-10)
					glVertex3f( 1000, 1000,-10)
					glVertex3f(-1000, 1000,-10)
					glEnd()
				for i in xrange(1, 15, 2):
					glStencilFunc(GL_EQUAL, i, 0xFF)
					glColor(float(i)/10, 0, 0)
					glBegin(GL_QUADS)
					glVertex3f(-1000,-1000,-10)
					glVertex3f( 1000,-1000,-10)
					glVertex3f( 1000, 1000,-10)
					glVertex3f(-1000, 1000,-10)
					glEnd()
				glPopMatrix()
				glDisable(GL_STENCIL_TEST)
				glEnable(GL_DEPTH_TEST)

			self._objectShader.unbind()

			glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
			glEnable(GL_BLEND)
			if self._objectLoadShader is not None:
				self._objectLoadShader.bind()
				glColor4f(0.2, 0.6, 1.0, 1.0)
				for obj in self._scene.objects():
					if obj._loadAnim is None:
						continue
					self._objectLoadShader.setUniform('intensity', obj._loadAnim.getPosition())
					self._objectLoadShader.setUniform('scale', obj.getBoundaryCircle() / 10)
					self._renderObject(obj)
				self._objectLoadShader.unbind()
				glDisable(GL_BLEND)

		self._drawMachine()

		if self.viewMode == 'gcode':
			if self._selectedObj is None:
				for element in self.modelSelectedButtonGroup:
					element._hidden = True
			# if self._gcodeLoadThread is not None and self._gcodeLoadThread.isAlive():
			# 	glDisable(GL_DEPTH_TEST)
			# 	glPushMatrix()
			# 	# glLoadIdentity()
			# 	glTranslatef(100,0,0)
			# 	glColor4ub(60,60,60,255)
			# 	print "cowcow"
			# 	opengl.glDrawStringCenter('Loading toolpath for visualization...')
			# 	glEnd()
			# 	glPopMatrix()
		else:
			#Draw the object box-shadow, so you can see where it will collide with other objects.
			if self._selectedObj is not None and len(self._scene.objects()) > 0:
				for element in self.modelSelectedButtonGroup:
					element._hidden = False
				size = self._selectedObj.getSize()[0:2] / 2 + self._scene.getObjectExtend()
				objectSize = self._selectedObj.getSize()[0:3]
				#print self._scene.getObjectExtend()
				glPushMatrix()
				glTranslatef(self._selectedObj.getPosition()[0], self._selectedObj.getPosition()[1], 0)

				isRotating = self.tool2.dragPlane != ''
				if self.tempMatrix is not None and not isRotating:
					objectSize = (numpy.matrix([objectSize]) * self.tempMatrix).getA().flatten()

				# if version.isDevVersion():
				# 	xynudge = 5
				# 	glTranslatef(size[0]+xynudge, 0, 0)
				# 	opengl.glDrawStringCenter("%0.1fmm" % (objectSize[1]))
				# 	glTranslatef(-size[0]-xynudge, -size[1]-xynudge, 0)
				# 	opengl.glDrawStringCenter("%0.1fmm" % (objectSize[0]))
				# 	glTranslatef(0, size[1]+xynudge, objectSize[2]+xynudge)
				# 	opengl.glDrawStringCenter("%0.1fmm" % (objectSize[2]))
				#
				# 	glTranslatef(0, 0, -objectSize[2]-xynudge)

				glEnable(GL_BLEND)
				glEnable(GL_CULL_FACE)
				glColor4f(0,0,0,0.12)
				glBegin(GL_QUADS)
				glVertex3f(-size[0],  size[1], 0.1)
				glVertex3f(-size[0], -size[1], 0.1)
				glVertex3f( size[0], -size[1], 0.1)
				glVertex3f( size[0],  size[1], 0.1)
				glEnd()
				glDisable(GL_CULL_FACE)
				glPopMatrix()
			else:
				for element in self.modelSelectedButtonGroup:
					element._hidden = True
			#Draw the outline of the selected object, on top of everything else except the GUI.
			if self._selectedObj is not None and self._selectedObj._loadAnim is None:
				glDisable(GL_DEPTH_TEST)
				glEnable(GL_CULL_FACE)
				glEnable(GL_STENCIL_TEST)
				glDisable(GL_BLEND)
				glStencilFunc(GL_EQUAL, 0, 255)

				glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
				glLineWidth(2)
				glColor4f(0,0,0,0.8)
				self._renderObject(self._selectedObj)
				glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

				glViewport(0, 0, self.GetSize().GetWidth(), self.GetSize().GetHeight())
				glDisable(GL_STENCIL_TEST)
				glDisable(GL_CULL_FACE)
				glEnable(GL_DEPTH_TEST)

			if self._selectedObj is not None:
				glPushMatrix()
				pos = self.getObjectCenterPos()
				glTranslate(pos[0], pos[1], pos[2])
				self.tool.OnDraw()
				self.tool2.OnDraw()
				glPopMatrix()
		if self.viewMode == 'overhang' and not opengl.hasShaderSupport():
			glDisable(GL_DEPTH_TEST)
			glPushMatrix()
			glLoadIdentity()
			glTranslate(0,-4,-10)
			glColor4ub(60,60,60,255)
			opengl.glDrawStringCenter('Overhang view not working due to lack of OpenGL shaders support.')
			glPopMatrix()

	def _renderObject(self, obj, brightness = False, addSink = False):
		glPushMatrix()
		if addSink:
			glTranslate(obj.getPosition()[0], obj.getPosition()[1], obj.getSize()[2] / 2 - profile.getProfileSettingFloat('object_sink'))
		else:
			glTranslate(obj.getPosition()[0], obj.getPosition()[1], obj.getSize()[2] / 2)

		if self.tempMatrix is not None and obj == self._selectedObj:
			tempMatrix = opengl.convert3x3MatrixTo4x4(self.tempMatrix)
			glMultMatrixf(tempMatrix)

		offset = obj.getDrawOffset()
		glTranslate(-offset[0], -offset[1], -offset[2] - obj.getSize()[2] / 2)

		tempMatrix = opengl.convert3x3MatrixTo4x4(obj.getMatrix())
		glMultMatrixf(tempMatrix)

		n = 0
		for m in obj._meshList:
			if m.vbo is None:
				m.vbo = opengl.GLVBO(m.vertexes, m.normal)
			if brightness:
				glColor4fv(map(lambda n: n * brightness, self._objColors[n]))
				n += 1
			m.vbo.render()
		glPopMatrix()


	def _drawMachine(self):
		#glEnable(GL_CULL_FACE)
		glEnable(GL_BLEND)
		#if profile.getPreference('machine_type') == 'ultimaker':

		glEnable(GL_FLAT);
		glEnable(GL_SMOOTH);
		glColor4f(.5,.5,.5,1)
		self._objectShader.bind()
		if self._machineSize[0] == 210:
			self._renderObject(self._platformditto, False, False)
			offset = 20
		elif self._machineSize[0] == 130:
			self._renderObject(self._platformlitto, False, False)
			offset = 15
		else:
			self._renderObject(self._platformdittopro, False, False)
			offset = 24
		self._objectShader.unbind()

		glColor4ub(0, 0, 0, 64)
		glLineWidth(1) #or whatever
		glPolygonMode(GL_FRONT_AND_BACK,GL_LINE)
		size = [profile.getPreferenceFloat('machine_width'), profile.getPreferenceFloat('machine_depth'), profile.getPreferenceFloat('machine_height')]
		v0 = [ size[0] / 2, size[1] / 2, size[2]]
		v1 = [ size[0] / 2,-size[1] / 2, size[2]]
		v2 = [-size[0] / 2, size[1] / 2, size[2]]
		v3 = [-size[0] / 2,-size[1] / 2, size[2]]
		v4 = [ size[0] / 2, size[1] / 2, 0]
		v5 = [ size[0] / 2,-size[1] / 2, 0]
		v6 = [-size[0] / 2, size[1] / 2, 0]
		v7 = [-size[0] / 2,-size[1] / 2, 0]

		vList = [v0,v1,v3,v2, v1,v0,v4,v5, v2,v3,v7,v6, v0,v2,v6,v4, v3,v1,v5,v7]
		glEnableClientState(GL_VERTEX_ARRAY)
		glVertexPointer(3, GL_FLOAT, 3*4, vList)



		#glColor4ub(5, 171, 231, 64)
		glDrawArrays(GL_QUADS, 0, 4)
		#glColor4ub(5, 171, 231, 96)
		glDrawArrays(GL_QUADS, 4, 8)
		#glColor4ub(5, 171, 231, 128)
		glDrawArrays(GL_QUADS, 12, 8)
		glDisableClientState(GL_VERTEX_ARRAY)




		sx = self._machineSize[0]
		sy = self._machineSize[1]
		for x in xrange(-int(sx/20)-1, int(sx / 20) + 1):
			for y in xrange(-int(sx/20)-1, int(sy / 20) + 1):
				x1 = x * 10
				x2 = x1 + 10
				y1 = y * 10
				y2 = y1 + 10
				x1 = max(min(x1, sx/2), -sx/2)
				y1 = max(min(y1, sy/2), -sy/2)
				x2 = max(min(x2, sx/2), -sx/2)
				y2 = max(min(y2, sy/2), -sy/2)
			#	if (x & 1) == (y & 1):
			#		glColor4ub(5, 171, 231, 127)
				#else:
				#	glColor4ub(5 * 8 / 10, 171 * 8 / 10, 231 * 8 / 10, 128)
				glBegin(GL_QUADS)
				glVertex3f(x1, y1, -0.02)
				glVertex3f(x2, y1, -0.02)
				glVertex3f(x2, y2, -0.02)
				glVertex3f(x1, y2, -0.02)
				glEnd()


		#Draw the object here
		glPolygonMode(GL_FRONT_AND_BACK,GL_FILL)

		#this is the grey ring around the grid. the shadow thing.
		glColor4ub(0, 0, 0, 32)
		glBegin(GL_QUADS)
		glVertex3f(-sx/2-offset, sy/2, -0.02)
		glVertex3f(sx/2+offset, sy/2, -0.02)
		glVertex3f(sx/2+offset, sy/2+offset, -0.02)
		glVertex3f(-sx/2-offset, sy/2+offset, -0.02)
		glEnd()

		glBegin(GL_QUADS)
		glVertex3f(-sx/2-offset, -sy/2, -0.02)
		glVertex3f(sx/2+offset, -sy/2, -0.02)
		glVertex3f(sx/2+offset, -sy/2-offset, -0.02)
		glVertex3f(-sx/2-offset, -sy/2-offset, -0.02)
		glEnd()

		glBegin(GL_QUADS)
		glVertex3f(-sx/2-offset, sy/2, -0.02)
		glVertex3f(-sx/2, sy/2, -0.02)
		glVertex3f(-sx/2, -sy/2, -0.02)
		glVertex3f(-sx/2-offset, -sy/2, -0.02)
		glEnd()

		glBegin(GL_QUADS)
		glVertex3f(sx/2, sy/2, -0.02)
		glVertex3f(sx/2+offset, sy/2, -0.02)
		glVertex3f(sx/2+offset, -sy/2, -0.02)
		glVertex3f(sx/2, -sy/2, -0.02)

		glEnd()

		glLineWidth(1) #also or whatever
		glColor4ub(0, 0, 0, 64)
		glDisable(GL_BLEND)
		#glDisable(GL_CULL_FACE)
	def compareLines(self, line1, line2):
		L1x1 = line1[0][0]
		L1x1 = "%.4f" % L1x1

		L1y1 = line1[0][1]
		L1y1 = "%.4f" % L1y1

		L1z1 = line1[0][2]
		L1z1 = "%.4f" % L1z1

		L1x2 = line1[1][0]
		L1x2 = "%.4f" % L1x2

		L1y2 = line1[1][1]
		L1y2 = "%.4f" % L1y2

		L1z2 = line1[1][2]
		L1z2 = "%.4f" % L1z2
		#----
		L2x1 = line2[0][0]
		L2x1 = "%.4f" % L2x1

		L2y1 = line2[0][1]
		L2y1 = "%.4f" % L2y1

		L2z1 = line2[0][2]
		L2z1 = "%.4f" % L2z1

		L2x2 = line2[1][0]
		L2x2 = "%.4f" % L2x2

		L2y2 = line2[1][1]
		L2y2 = "%.4f" % L2y2

		L2z2 = line2[1][2]
		L2z2 = "%.4f" % L2z2

		if L1x1 == L2x1 and L1y1 == L2y1 and L1z1 == L2z1 and L1x2 == L2x2 and L1y2 == L2y2 and L1z2 == L2z2:
			#print "why"
			return True
		else:
			#print L1x1 , L2x1, L1y1 , L2y1, L1z1 , L2z1 , L1x2 , L2x2, L1y2 , L2y2, L1z2 , L2z2
			return False
	def compareLines2(self, line1, line2): #this one uses the format [0,1,2,3,4,5] for line 1 only
		L1x1 = line1[0]
		L1x1 = "%.4f" % L1x1

		L1y1 = line1[1]
		L1y1 = "%.4f" % L1y1

		#L1z1 = line1[2]
		#L1z1 = "%.4f" % L1z1

		L1x2 = line1[3]
		L1x2 = "%.4f" % L1x2

		L1y2 = line1[4]
		L1y2 = "%.4f" % L1y2

		#L1z2 = line1[5]
		#L1z2 = "%.4f" % L1z2
		#----
		L2x1 = line2[0][0]
		L2x1 = "%.4f" % L2x1

		L2y1 = line2[0][1]
		L2y1 = "%.4f" % L2y1

		#L2z1 = line2[0][2]
		#L2z1 = "%.4f" % L2z1

		L2x2 = line2[1][0]
		L2x2 = "%.4f" % L2x2

		L2y2 = line2[1][1]
		L2y2 = "%.4f" % L2y2

		#L2z2 = line2[1][2]
		#L2z2 = "%.4f" % L2z2

		#if L1x1 == L2x1 and L1y1 == L2y1 and L1z1 == L2z1 and L1x2 == L2x2 and L1y2 == L2y2 and L1z2 == L2z2:
		if L1x1 == L2x1 and L1y1 == L2y1 and L1x2 == L2x2 and L1y2 == L2y2:
			#print "why"
			return True
		else:
			#print L1x1 , L2x1, L1y1 , L2y1, L1z1 , L2z1 , L1x2 , L2x2, L1y2 , L2y2, L1z2 , L2z2
			return False

	def _generateGCodeVBOs(self, layer):
		ret = []
		#supportLines = set() #sets have no repeating elements
		blag = []
		blag.append([[ 113.360,94.400,0.3],[ 113.360,85.220,0.3]])
		blag.append([[ 113.360,85.220,0.3],[ 121.070,85.220,0.3]])
		#blag.append([[ 50.381,55.733,0.9],[ 79.619,55.733,0.9]])
		#blag.append([[ 50.381,55.733,1.2],[ 79.619,55.733,1.2]])

		for extrudeType in ['WALL-OUTER:0', 'WALL-OUTER:1', 'WALL-OUTER:2', 'WALL-OUTER:3', 'WALL-INNER', 'FILL', 'SKIRT', 'SUPPORT', 'SKIN']:
			if ':' in extrudeType:
				extruder = int(extrudeType[extrudeType.find(':')+1:])
				extrudeType = extrudeType[0:extrudeType.find(':')]
			else:
				extruder = None
			pointList = numpy.zeros((0,3), numpy.float32)
			pointListSupport2 = numpy.zeros((0,3), numpy.float32)

			count = 0
			for path in layer:

				if path['type'] == 'extrude' and path['pathType'] == extrudeType and (extruder is None or path['extruder'] == extruder):
					a = path['points']
					a = numpy.concatenate((a[:-1], a[1:]), 1)
					b = a
					#print "old:"
					#print b
					#print "new:"
					a = a.reshape((len(a) * 2, 3))
					#print a
					#print "try:"
					#c = a.reshape((len(a) / 2, 6))
					#print c
					#print "---"
					#print len(a)
					if extrudeType == 'SUPPORT':
						for j in b:
							x1 = j[0]
							y1 = j[1]
							x2 = j[3]
							y2 = j[4]
							z = j[5]

							#c.reshape((len(c) * 2, 3))

							line = ((x1,y1,z),(x2,y2,z)) #can I just use j here instead?
							self.supportLines.append(line)
							#print self.supportLines
						#self.supportLines = numpy.concatenate((self.supportLines, b))
						#print self.supportLines
						found = False
						for line in []: #blag will turn into self.trimList
							#print line
							#print a
							#print "---"
							if self.compareLines(a,line):
								#pointListSupport2 = numpy.concatenate((pointListSupport2, a))
								found = True

						if not found:
							pointList = numpy.concatenate((pointList, a))
							#print pointListSupport2

					else:
						pointList = numpy.concatenate((pointList, a))
						"""
				if extrudeType == 'SUPPORT':
						# in here, make a b and c
						# b will have lines that are not selected, c are selected
						# iterate through a and then put not selected into b, selected into c
						b = numpy.array([])

						for k in a:
							numpy.concatenate(b,k)
						if a == b:
							print "they are equal"
						print b
						for j in b:
							x1 = j[0]
							y1 = j[1]
							x2 = j[3]
							y2 = j[4]
							z = j[5]

							#c.reshape((len(c) * 2, 3))
							if x1 == x2 and y1 == y2:
								pass
							else:
								line = ((x1,y1,z),(x2,y2,z)) #can I just use j here instead?
								self.supportLines.add(line)
							#print len(self.supportLines)
							#print line
							#print "------"
					else:
						c = 0
					"""
			#print pointList
			ret.append(opengl.GLVBO(pointList))
			if extrudeType == 'SUPPORT':
				ret.append(opengl.GLVBO(pointListSupport2))
				#print "bonus"
				#print pointList


			#print supportLines[0]
			#for q in supportLines:
			#	print q[0][0]
			#print "----"
		return ret

	def _generateGCodeVBOs2(self, layer):
		filamentRadius = profile.getProfileSettingFloat('filament_diameter') / 2
		filamentArea = math.pi * filamentRadius * filamentRadius

		#print layer
		ret = []
		for extrudeType in ['WALL-OUTER:0', 'WALL-OUTER:1', 'WALL-OUTER:2', 'WALL-OUTER:3', 'WALL-INNER', 'FILL', 'SKIRT', 'SUPPORT', 'SKIN']:
			if ':' in extrudeType:
				extruder = int(extrudeType[extrudeType.find(':')+1:])
				extrudeType = extrudeType[0:extrudeType.find(':')]
			else:
				extruder = None
			pointList = numpy.zeros((0,3), numpy.float32)
			for path in layer:
				if path['type'] == 'extrude' and path['pathType'] == extrudeType and (extruder is None or path['extruder'] == extruder):
					a = path['points']
					if extrudeType == 'FILL':
						a[:,2] += 0.01

					normal = a[1:] - a[:-1]
					lens = numpy.sqrt(normal[:,0]**2 + normal[:,1]**2)
					normal[:,0], normal[:,1] = -normal[:,1] / lens, normal[:,0] / lens
					normal[:,2] /= lens

					ePerDist = path['extrusion'][1:] / lens
					lineWidth = ePerDist * (filamentArea / path['layerThickness'] / 2)

					normal[:,0] *= lineWidth
					normal[:,1] *= lineWidth

					b = numpy.zeros((len(a)-1, 0), numpy.float32)
					b = numpy.concatenate((b, a[1:] + normal), 1)
					b = numpy.concatenate((b, a[1:] - normal), 1)
					b = numpy.concatenate((b, a[:-1] - normal), 1)
					b = numpy.concatenate((b, a[:-1] + normal), 1)
					b = b.reshape((len(b) * 4, 3))

					if len(a) > 2:
						normal2 = normal[:-1] + normal[1:]
						lens2 = numpy.sqrt(normal2[:,0]**2 + normal2[:,1]**2)
						normal2[:,0] /= lens2
						normal2[:,1] /= lens2
						normal2[:,0] *= lineWidth[:-1]
						normal2[:,1] *= lineWidth[:-1]

						c = numpy.zeros((len(a)-2, 0), numpy.float32)
						c = numpy.concatenate((c, a[1:-1]), 1)
						c = numpy.concatenate((c, a[1:-1]+normal[1:]), 1)
						c = numpy.concatenate((c, a[1:-1]+normal2), 1)
						c = numpy.concatenate((c, a[1:-1]+normal[:-1]), 1)

						c = numpy.concatenate((c, a[1:-1]), 1)
						c = numpy.concatenate((c, a[1:-1]-normal[1:]), 1)
						c = numpy.concatenate((c, a[1:-1]-normal2), 1)
						c = numpy.concatenate((c, a[1:-1]-normal[:-1]), 1)

						c = c.reshape((len(c) * 8, 3))
						pointList = numpy.concatenate((pointList, b, c))
					else:
						pointList = numpy.concatenate((pointList, b))
			ret.append(opengl.GLVBO(pointList))
			if extrudeType == 'SUPPORT':
					ret.append(opengl.GLVBO(pointList))
		pointList = numpy.zeros((0,3), numpy.float32)
		for path in layer:
			if path['type'] == 'move':
				a = path['points'] + numpy.array([0,0,0.01], numpy.float32)
				a = numpy.concatenate((a[:-1], a[1:]), 1)
				a = a.reshape((len(a) * 2, 3))
				pointList = numpy.concatenate((pointList, a))
			if path['type'] == 'retract':
				a = path['points'] + numpy.array([0,0,0.01], numpy.float32)
				a = numpy.concatenate((a[:-1], a[1:] + numpy.array([0,0,1], numpy.float32)), 1)
				a = a.reshape((len(a) * 2, 3))
				pointList = numpy.concatenate((pointList, a))
		ret.append(opengl.GLVBO(pointList))

		return ret

	def getObjectCenterPos(self):
		if self._selectedObj is None:
			return [0.0, 0.0, 0.0]
		pos = self._selectedObj.getPosition()
		size = self._selectedObj.getSize()
		return [pos[0], pos[1], size[2]/2]

	def getObjectBoundaryCircle(self):
		if self._selectedObj is None:
			return 0.0
		return self._selectedObj.getBoundaryCircle()

	def getObjectSize(self):
		if self._selectedObj is None:
			return [0.0, 0.0, 0.0]
		return self._selectedObj.getSize()

	def getObjectMatrix(self):
		if self._selectedObj is None:
			return numpy.matrix([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
		return self._selectedObj.getMatrix()

class shaderEditor(wx.Dialog):
	def __init__(self, parent, callback, v, f):
		super(shaderEditor, self).__init__(parent, title="Shader editor", style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
		self._callback = callback
		s = wx.BoxSizer(wx.VERTICAL)
		self.SetSizer(s)
		self._vertex = wx.TextCtrl(self, -1, v, style=wx.TE_MULTILINE)
		self._fragment = wx.TextCtrl(self, -1, f, style=wx.TE_MULTILINE)
		s.Add(self._vertex, 1, flag=wx.EXPAND)
		s.Add(self._fragment, 1, flag=wx.EXPAND)

		self._vertex.Bind(wx.EVT_TEXT, self.OnText, self._vertex)
		self._fragment.Bind(wx.EVT_TEXT, self.OnText, self._fragment)

		self.SetPosition(self.GetParent().GetPosition())
		self.SetSize((self.GetSize().GetWidth(), self.GetParent().GetSize().GetHeight()))
		self.Show()

	def OnText(self, e):
		self._callback(self._vertex.GetValue(), self._fragment.GetValue())

class ProjectObject(object):
	def __init__(self, parent, filename):
		super(ProjectObject, self).__init__()
		#print filename
		self.mesh = meshLoader.loadMesh(filename)

		self.parent = parent
		self.filename = filename
		self.scale = 1.0
		self.rotate = 0.0
		self.flipX = False
		self.flipY = False
		self.flipZ = False
		self.swapXZ = False
		self.swapYZ = False
		self.extruder = 0
		self.profile = None
		
		self.modelDisplayList = None
		self.modelDirty = False

		try:
			self.mesh.getMinimumZ()
		except:
			pass

		#print self.mesh.getMinimumZ()
		
		self.centerX = -self.getMinimum()[0] + 5
		self.centerY = -self.getMinimum()[1] + 5
		
		self.updateModelTransform()

		self.centerX = -self.getMinimum()[0] + 5
		self.centerY = -self.getMinimum()[1] + 5

	def isSameExceptForPosition(self, other):
		if self.filename != other.filename:
			return False
		if self.scale != other.scale:
			return False
		if self.rotate != other.rotate:
			return False
		if self.flipX != other.flipX:
			return False
		if self.flipY != other.flipY:
			return False
		if self.flipZ != other.flipZ:
			return False
		if self.swapXZ != other.swapXZ:
			return False
		if self.swapYZ != other.swapYZ:
			return False
		if self.extruder != other.extruder:
			return False
		if self.profile != other.profile:
			return False
		return True

	def updateModelTransform(self):
		self.mesh.setRotateMirror(self.rotate, self.flipX, self.flipY, self.flipZ, self.swapXZ, self.swapYZ)
		minZ = self.mesh.getMinimumZ()
		minV = self.getMinimum()
		maxV = self.getMaximum()
		self.mesh.vertexes -= numpy.array([minV[0] + (maxV[0] - minV[0]) / 2, minV[1] + (maxV[1] - minV[1]) / 2, minZ])
		minZ = self.mesh.getMinimumZ()
		self.modelDirty = True
	
	def getMinimum(self):
		return self.mesh.getMinimum()
	def getMaximum(self):
		return self.mesh.getMaximum()
	def getSize(self):
		return self.mesh.getSize()
	
	def clone(self):
		p = ProjectObject(self.parent, self.filename)

		p.centerX = self.centerX + 5
		p.centerY = self.centerY + 5
		
		p.filename = self.filename
		p.scale = self.scale
		p.rotate = self.rotate
		p.flipX = self.flipX
		p.flipY = self.flipY
		p.flipZ = self.flipZ
		p.swapXZ = self.swapXZ
		p.swapYZ = self.swapYZ
		p.extruder = self.extruder
		p.profile = self.profile
		
		p.updateModelTransform()
		
		return p
	
	def clampXY(self):
		if self.centerX < -self.getMinimum()[0] * self.scale + self.parent.extruderOffset[self.extruder][0]:
			self.centerX = -self.getMinimum()[0] * self.scale + self.parent.extruderOffset[self.extruder][0]
		if self.centerY < -self.getMinimum()[1] * self.scale + self.parent.extruderOffset[self.extruder][1]:
			self.centerY = -self.getMinimum()[1] * self.scale + self.parent.extruderOffset[self.extruder][1]
		if self.centerX > self.parent.machineSize[0] + self.parent.extruderOffset[self.extruder][0] - self.getMaximum()[0] * self.scale:
			self.centerX = self.parent.machineSize[0] + self.parent.extruderOffset[self.extruder][0] - self.getMaximum()[0] * self.scale
		if self.centerY > self.parent.machineSize[1] + self.parent.extruderOffset[self.extruder][1] - self.getMaximum()[1] * self.scale:
			self.centerY = self.parent.machineSize[1] + self.parent.extruderOffset[self.extruder][1] - self.getMaximum()[1] * self.scale
			
def getCodeInt(line, code):
	n = line.find(code) + 1
	if n < 1:
		return None
	m = line.find(' ', n)
	try:
		if m < 0:
			return int(line[n:])
		return int(line[n:m])
	except:
		return None

def getCodeFloat(line, code):
	n = line.find(code) + 1
	if n < 1:
		return None
	m = line.find(' ', n)
	try:
		if m < 0:
			return float(line[n:])
		return float(line[n:m])
	except:
		return None