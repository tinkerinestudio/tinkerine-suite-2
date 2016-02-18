from __future__ import absolute_import
from __future__ import division
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import traceback
import sys
import os
import time
from wx import glcanvas
import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL.GL import *

from Cura.util import profile
from Cura.util import version
from Cura.gui.util import opengl
from Cura.gui.util import tooltipText
import platform

class animation(object):
	def __init__(self, gui, start, end, runTime):
		self._start = start
		self._end = end
		self._startTime = time.time()
		self._runTime = runTime
		gui._animationList.append(self)

	def isDone(self):
		return time.time() > self._startTime + self._runTime

	def getPosition(self):
		if self.isDone():
			return self._end
		f = (time.time() - self._startTime) / self._runTime
		ts = f*f
		tc = f*f*f
		#f = 6*tc*ts + -15*ts*ts + 10*tc
		f = tc + -3*ts + 3*f
		return self._start + (self._end - self._start) * f

class Tooltip(wx.Panel):
	"A base class for configuration dialogs. Handles creation of settings, and popups"
	def __init__(self, parent):
		super(Tooltip, self).__init__(parent)
		
		self.settingControlList = []
		
		#Create the popup window
		self.popup = wx.PopupWindow(self, flags=wx.BORDER_SIMPLE)
		self.popup.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOBK))
		self.popup.setting = None
		self.popup.text = wx.StaticText(self.popup, -1, 'aaaaaaa');
		self.popup.sizer = wx.BoxSizer()
		self.popup.sizer.Add(self.popup.text, flag=wx.EXPAND|wx.ALL, border=1)
		self.popup.SetSizer(self.popup.sizer)
		
		self.timer = 0
		
		self.showing = False
		self._parent = parent

	def OnPopupDisplay(self, setting, x, y):
		self.timer += 1
		#print self.timer
		self.popup.setting = setting
		self.UpdatePopup(setting, x, y)
		self.popup.Show()
		self.showing = True
		#print self.popup.IsShown()
		#print "AHAH"
		
	def OnPopupHide(self, e):
		self.popup.Hide()
		self.showing = False
	
	def UpdatePopup(self, setting, x, y):
		if self.popup.setting == setting:
			#if setting.validationMsg != '':
			#	self.popup.text.SetLabel(setting.validationMsg + '\n\n' + setting.helpText)
			#else:
			self.popup.text.SetLabel(setting)
			self.popup.text.Wrap(350)
			self.popup.Fit()
			#x, y = setting.ctrl.ClientToScreenXY(0, 0)
			#sx, sy = setting.ctrl.GetSizeTuple()
			#if platform.system() == "Windows":
			#	for some reason, under windows, the popup is relative to the main window... in some cases. (Wierd ass bug)
			#	wx, wy = self.ClientToScreenXY(0, 0)
				#x -= wx
				#y -= wy
			wx, wy = self.ClientToScreenXY(0, 0)
			w, h = self._parent.GetSize()
			#print wx, wy
			#print w, h
			self.popup.SetPosition((wx+x+30, wy+y-30))

class glGuiControl(object):
	def __init__(self, parent, pos):
		self._parent = parent
		self._base = parent._base
		self._pos = pos
		self._size = (0,0, 1, 1)
		self._parent.add(self)

		self.YnudgeModifer = 85

		self.buttonTitleTextColour = (88,89,91)
		self.buttonTooltipTextColour = (255,255,255)
		self.buttonSelectedColour = (100,100,100)
		self.buttonUnselectedColour = (255,255,255,255)
		self.buttonHighlightColour = (255,255,255)
		self.altButtonHighlightColour = (255,255,255)

		self.settingsTextColour = (35,140,90)
		self.settingsSelectedColour = (241,102,89)
		self.settingsUnselectedColour = (150,150,150)

		self._xBreakpointNudge = -60

	def setSize(self, x, y, w, h):
		self._size = (x, y, w, h)

	def getSize(self):
		return self._size

	def getMinSize(self):
		return 1, 1

	def updateLayout(self):
		pass

	def focusNext(self):
		for n in xrange(self._parent._glGuiControlList.index(self) + 1, len(self._parent._glGuiControlList)):
			if self._parent._glGuiControlList[n].setFocus():
				return
		for n in xrange(0, self._parent._glGuiControlList.index(self)):
			if self._parent._glGuiControlList[n].setFocus():
				return

	def focusPrevious(self):
		for n in xrange(self._glGuiControlList.index(self) -1, -1, -1):
			if self._glGuiControlList[n].setFocus():
				return
		for n in xrange(len(self._glGuiControlList) - 1, self._glGuiControlList.index(self), -1):
			if self._glGuiControlList[n].setFocus():
				return

	def setFocus(self):
		return False

	def hasFocus(self):
		return self._base._focus == self

	def OnMouseUp(self, x, y):
		pass

	def OnKeyChar(self, key):
		pass

class glGuiContainer(glGuiControl):
	def __init__(self, parent, pos):
		self._glGuiControlList = []
		glGuiLayoutButtons(self)
		super(glGuiContainer, self).__init__(parent, pos)

	def add(self, ctrl):
		self._glGuiControlList.append(ctrl)
		self.updateLayout()

	def OnMouseDown(self, x, y, button):
		for ctrl in reversed(self._glGuiControlList):
			if ctrl.OnMouseDown(x, y, button):
				return True
		return False

	def OnMouseUp(self, x, y):
		for ctrl in self._glGuiControlList:
			if ctrl.OnMouseUp(x, y):
				return True
		return False

	def OnMouseMotion(self, x, y):
		handled = False
		for ctrl in self._glGuiControlList:
			if ctrl.OnMouseMotion(x, y):
				handled = True
		return handled

	def draw(self):
		for ctrl in self._glGuiControlList:
			ctrl.draw()

	def updateLayout(self):
		self._layout.update()
		for ctrl in self._glGuiControlList:
			ctrl.updateLayout()

class glGuiPanel(glcanvas.GLCanvas):
	def __init__(self, parent):
		attribList = (glcanvas.WX_GL_RGBA, glcanvas.WX_GL_DOUBLEBUFFER, glcanvas.WX_GL_DEPTH_SIZE, 24, glcanvas.WX_GL_STENCIL_SIZE, 8, 0)
		glcanvas.GLCanvas.__init__(self, parent, style=wx.WANTS_CHARS, attribList = attribList)
		self._base = self
		self._focus = None
		self._container = None
		self._container = glGuiContainer(self, (0,0))
		self._shownError = False
		self._parent = parent

		self._context = glcanvas.GLContext(self)
		self._glButtonsTexture = None
		#self._glButtonsSettingsTexture = None
		#self._glRobotTexture = None
		#self._glLittoTexture = None
		#self._glBlackBoxTexture = None
		self._buttonSize = 72

		self._animationList = []
		self.glReleaseList = []
		self._refreshQueued = False
		self.bla = 0
		self.properScaledWidth = 994

		self.tourCount = 0
		self.tourDictionary = {}
		self.tourNudgeDictionary = {}

		wx.EVT_PAINT(self, self._OnGuiPaint)
		wx.EVT_SIZE(self, self._OnSize)
		wx.EVT_ERASE_BACKGROUND(self, self._OnEraseBackground)
		
		self.loaded = False
		glColor4ub(255,255,255,255)
		wx.EVT_LEFT_DOWN(self, self._OnGuiMouseDown)
		wx.EVT_LEFT_DCLICK(self, self._OnGuiMouseDown)
		wx.EVT_LEFT_UP(self, self._OnGuiMouseUp)
		wx.EVT_RIGHT_DOWN(self, self._OnGuiMouseDown)
		wx.EVT_RIGHT_DCLICK(self, self._OnGuiMouseDown)
		wx.EVT_RIGHT_UP(self, self._OnGuiMouseUp)
		wx.EVT_MIDDLE_DOWN(self, self._OnGuiMouseDown)
		wx.EVT_MIDDLE_DCLICK(self, self._OnGuiMouseDown)
		wx.EVT_MIDDLE_UP(self, self._OnGuiMouseUp)
		wx.EVT_MOTION(self, self._OnGuiMouseMotion)
		wx.EVT_CHAR(self, self._OnGuiKeyChar)
		wx.EVT_KILL_FOCUS(self, self.OnFocusLost)
		wx.EVT_IDLE(self, self._OnIdle)
		
		self._progressBar = None
		
	def setProgressBar(self, value):
		self._progressBar = value

	def getProgressBar(self):
		return self._progressBar

	def _OnIdle(self, e):
		if len(self._animationList) > 0 or self._refreshQueued:
			self._refreshQueued = False
			for anim in self._animationList:
				if anim.isDone():
					self._animationList.remove(anim)
			self.Refresh()

	def _OnGuiKeyChar(self, e):
		if self._focus is not None:
			self._focus.OnKeyChar(e.GetKeyCode())
			self.Refresh()
		else:
			self.OnKeyChar(e.GetKeyCode())

	def OnFocusLost(self, e):
		self._focus = None
		self.Refresh()

	def _OnGuiMouseDown(self,e):
		self.SetFocus()
		if self._container.OnMouseDown(e.GetX(), e.GetY(), e.GetButton()):
			self.Refresh()
			return
		self.OnMouseDown(e)

	def _OnGuiMouseUp(self, e):
		if self._container.OnMouseUp(e.GetX(), e.GetY()):
			self.Refresh()
			return
		self.OnMouseUp(e)

	def _OnGuiMouseMotion(self,e):
		self.Refresh()
		if not self._container.OnMouseMotion(e.GetX(), e.GetY()):
			self.OnMouseMotion(e)

	def _OnGuiPaint(self, e):
		h = self.GetSize().GetHeight()
		w = self.GetSize().GetWidth()
		#oldButtonSize = self._buttonSize
		#if h / 3 < w / 4:
		#	w = h * 4 / 3
		#if w < 64 * 8:
		#	self._buttonSize = 32
		#elif w < 64 * 10:
		#	self._buttonSize = 48
		#elif w < 64 * 15:
		#	self._buttonSize = 64
		#elif w < 64 * 20:
		#	self._buttonSize = 80
		#else:
		#	self._buttonSize = 96
		#if self._buttonSize != oldButtonSize:
			#self._container.updateLayout()

		dc = wx.PaintDC(self)
		try:
			self.SetCurrent(self._context)
			for obj in self.glReleaseList:
				obj.release()
			del self.glReleaseList[:]
			renderStartTime = time.time()
			self.OnPaint(e)
			self._drawGui()
			glFlush()
			glLoadIdentity()
			glTranslate(10, self.GetSize().GetHeight() - 85, -1)
			glColor4f(0.2,0.2,0.2,0.5)
			opengl.glDrawStringLeft("%s" % profile.getPreference('selectedfile'))
			if version.isDevVersion():
				renderTime = time.time() - renderStartTime
				if renderTime != 0:
					glTranslate(0, -25, -1)
					opengl.glDrawStringLeft("fps:%d" % (1 / renderTime))

			self.SwapBuffers()
		except:
			errStr = 'An error has occurred during the 3D view drawing.'
			tb = traceback.extract_tb(sys.exc_info()[2])
			errStr += "\n%s: '%s'" % (str(sys.exc_info()[0].__name__), str(sys.exc_info()[1]))
			for n in xrange(len(tb)-1, -1, -1):
				locationInfo = tb[n]
				errStr += "\n @ %s:%s:%d" % (os.path.basename(locationInfo[0]), locationInfo[2], locationInfo[1])
			if not self._shownError:
				wx.CallAfter(wx.MessageBox, errStr, '3D window error', wx.OK | wx.ICON_EXCLAMATION)
				self._shownError = True

	def _drawGui(self):
		mainWindow = self.GetParent().GetParent()

		if self._glButtonsTexture is None:

			self._glButtonsTexture = opengl.loadGLTexture('glButtons-sheet-new-1.png')
			self._glButtonsTexture2 = opengl.loadGLTexture('glButtons-sheet-new-2.png')
			self._glSuiteTexture = opengl.loadGLTexture(_('Logo_suite.png'))
			self._glScaleBoxTexture = opengl.loadGLTexture('scale_boxes.png')

			self._tourTexture00 = opengl.loadGLTexture('tour00.jpg')
			self._tourTexture01 = opengl.loadGLTexture('tour01.jpg')
			self._tourTexture02 = opengl.loadGLTexture('tour02.jpg')
			self._tourTexture03 = opengl.loadGLTexture('tour03.jpg')
			self._tourTexture04 = opengl.loadGLTexture('tour04.jpg')
			self._tourTexture05 = opengl.loadGLTexture('tour05.jpg')
			self._tourTexture06 = opengl.loadGLTexture('tour06.jpg')
			self._tourTexture07 = opengl.loadGLTexture('tour07.jpg')
			self._tourTexture08 = opengl.loadGLTexture('tour08.jpg')
			self._tourTexture09 = opengl.loadGLTexture('tour09.jpg')
			self._tourTexture10 = opengl.loadGLTexture('tour10.jpg')

			self.tourDictionary[0] = self._tourTexture00
			self.tourDictionary[1] = self._tourTexture01
			self.tourDictionary[2] = self._tourTexture02
			self.tourDictionary[3] = self._tourTexture03
			self.tourDictionary[4] = self._tourTexture04
			self.tourDictionary[5] = self._tourTexture05
			self.tourDictionary[6] = self._tourTexture06
			self.tourDictionary[7] = self._tourTexture07
			self.tourDictionary[8] = self._tourTexture08
			self.tourDictionary[9] = self._tourTexture09 #Keyboard shortcuts
			self.tourDictionary[10] = self._tourTexture10

			if profile.getPreference('first_run_tour_done') == 'False':
				mainWindow.SetSize((1024,768))
				self.properScaledWidth = self._parent.GetSize()[0]

			if platform.system() == 'Windows':
				macNudge = 0
			else:
				macNudge = 20
			self.tourNudgeDictionary[0] = (0,0)
			self.tourNudgeDictionary[1] = (150,100+macNudge)
			self.tourNudgeDictionary[2] = (190,100+macNudge)
			self.tourNudgeDictionary[3] = (0,360+macNudge)
			self.tourNudgeDictionary[4] = (225,100+macNudge)
			self.tourNudgeDictionary[5] = (-165,355+macNudge)
			self.tourNudgeDictionary[6] = (0,355+macNudge)
			self.tourNudgeDictionary[7] = (230,360+macNudge)
			self.tourNudgeDictionary[8] = (190,360+macNudge)
			self.tourNudgeDictionary[9] = (363,-145+macNudge)
			self.tourNudgeDictionary[10] = (-1500,-1000)

		glDisable(GL_DEPTH_TEST)
		glEnable(GL_BLEND)
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
		glDisable(GL_LIGHTING)
		glColor4ub(255,255,255,255)

		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		size = self.GetSize()
		glOrtho(0, size.GetWidth()-1, size.GetHeight()-1, 0, -1000.0, 1000.0)
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		glEnd()
		glDisable(GL_TEXTURE_2D)
		glPopMatrix()

		glBindTexture(GL_TEXTURE_2D, self._glButtonsTexture)
		glEnable(GL_TEXTURE_2D)
		glPushMatrix()
		glColor3ub(255,255,255)
		opengl.glDrawTexturedQuad(0, 0, self.GetSize().GetWidth(), self._buttonSize, 0)

		# if self.viewMode == 'gcode' :
		# 	glColor4ub(255,255,255,215)
		# 	opengl.glDrawTexturedQuad(0, self.GetSize().GetHeight()-80, self.GetSize().GetWidth(), 80, 0)
		if self._selectedObj is not None or self.viewMode == 'gcode':
			glColor4ub(255,255,255,215)
			opengl.glDrawTexturedQuad(0, self.GetSize().GetHeight()-self._buttonSize, self.GetSize().GetWidth(), self._buttonSize, 0)
		# if self._selectedObj is not None:
		# 	glDisable(GL_TEXTURE_2D)
		# 	glPopMatrix()
		# 	glBindTexture(GL_TEXTURE_2D, self._glScaleBoxTexture)
		#
		# 	glEnable(GL_TEXTURE_2D)
		# 	glPushMatrix()
		# 	glColor4f(1,1,1,1)
		# 	glTranslate(1000, 1000,0)
		# 	glScale( 512,32,0)
		#
		# 	glBegin(GL_QUADS)
		# 	glTexCoord2f(1, 0)
		# 	glVertex2f(0,-1)
		# 	glTexCoord2f(0, 0)
		# 	glVertex2f(-1,-1)
		# 	glTexCoord2f(0, 1)
		# 	glVertex2f(-1, 0)
		# 	glTexCoord2f(1, 1)
		# 	glVertex2f(0, 0)
		# 	glEnd()
		# 	glDisable(GL_TEXTURE_2D)
		# 	glPopMatrix()

		glDisable(GL_TEXTURE_2D)
		glPopMatrix()
		glBindTexture(GL_TEXTURE_2D, self._glSuiteTexture)

		glEnable(GL_TEXTURE_2D)
		glPushMatrix()
		glColor4f(1,1,1,1)
		glTranslate(267, 66,0)
		glScale( 256,64,0)

		glBegin(GL_QUADS)
		glTexCoord2f(1, 0)
		glVertex2f(0,-1)
		glTexCoord2f(0, 0)
		glVertex2f(-1,-1)
		glTexCoord2f(0, 1)
		glVertex2f(-1, 0)
		glTexCoord2f(1, 1)
		glVertex2f(0, 0)
		glEnd()
		glPopMatrix()
		glDisable(GL_TEXTURE_2D)
		self._container.draw()

		if self.showKeyboardShortcuts == True:
			glBindTexture(GL_TEXTURE_2D, self.tourDictionary[9])

			glEnable(GL_TEXTURE_2D)
			glPushMatrix()

			(width, height) = self.GetSize()

			adjustedWidth = 900
			adjustedHeight = 675

			glTranslate(adjustedWidth+(width-adjustedWidth)/2, adjustedHeight+(height-adjustedHeight)/2, 0)
			glScale(adjustedWidth, adjustedHeight,0)

			# mainWindow.SetMinSize((1024,768))
			# mainWindow.SetMaxSize((1024,768))


			glBegin(GL_QUADS)
			glTexCoord2f(1, 0)
			glVertex2f(0,-1)
			glTexCoord2f(0, 0)
			glVertex2f(-1,-1)
			glTexCoord2f(0, 1)
			glVertex2f(-1, 0)
			glTexCoord2f(1, 1)
			glVertex2f(0, 0)
			glEnd()
			glDisable(GL_TEXTURE_2D)
			glPopMatrix()

			self.greyBackground.setDisabled(False)
			self.greyBackground.setHidden(False)
			# self.closeKeyboardShortcuts.setDisabled(False)
			# self.closeKeyboardShortcuts.setHidden(False)
			self.closeKeyboardShortcutsButton._Ynudge = (height - adjustedHeight - 13)/2
			self.closeKeyboardShortcutsButton.setDisabled(False)
			self.closeKeyboardShortcutsButton.setHidden(False)
			self.closeKeyboardShortcutsButton.draw()


		if profile.getPreference('first_run_tour_done') == 'False':
			try:
				glBindTexture(GL_TEXTURE_2D, self.tourDictionary[self.tourCount])
			except KeyError:
				print "no texture to get from self.tourDictionary"

			#mainWindow.SetSize((1024,768))
			panelSize = self._parent.GetSize()

			width = 1024
			height = panelSize[1]

			scale = float(height)/768.0

			scaledWidth = width * scale

			mainWindow.SetMinSize((width-(self.properScaledWidth-scaledWidth),768))
			mainWindow.SetMaxSize((width-(self.properScaledWidth-scaledWidth),768))

			mainWindow.SetSize((width-(self.properScaledWidth-scaledWidth),768))

			glEnable(GL_TEXTURE_2D)
			glPushMatrix()
			glTranslate(scaledWidth, height, 0)
			glScale(scaledWidth, height, 0)

			glBegin(GL_QUADS)
			glTexCoord2f(1, 0)
			glVertex2f(0,-1)
			glTexCoord2f(0, 0)
			glVertex2f(-1,-1)
			glTexCoord2f(0, 1)
			glVertex2f(-1, 0)
			glTexCoord2f(1, 1)
			glVertex2f(0, 0)
			glEnd()
			glDisable(GL_TEXTURE_2D)
			glPopMatrix()

			self.whiteBackground2.setDisabled(False)
			self.whiteBackground2.setHidden(False)

			if self.tourCount == 0:
				for item in self.startTourGroup:
					item.setHidden(False)
					item.setDisabled(False)
					item.draw()
			elif self.tourCount == 9:
				for item in self.tourGroup:
					item._Xnudge = self.tourNudgeDictionary[self.tourCount][0]
					item._Ynudge = self.tourNudgeDictionary[self.tourCount][1]
					item.setHidden(False)
					item.setDisabled(False)
					self.feelingReadyText.setHidden(True)
					self.skipTourText.setHidden(True)
					item.draw()
				for item in self.startTourGroup:
					item.setHidden(True)
					item.setDisabled(True)

			elif self.tourCount == 10:
				for item in self.endTourGroup:
					item.setHidden(False)
					item.setDisabled(False)
					item.draw()

				for item in self.tourGroup:
					item.setHidden(True)
					item.setDisabled(True)
			else:
				for item in self.tourGroup:
					item._Xnudge = self.tourNudgeDictionary[self.tourCount][0]
					item._Ynudge = self.tourNudgeDictionary[self.tourCount][1]
					item.setHidden(False)
					item.setDisabled(False)
					item.draw()
				for item in self.startTourGroup:
					item.setHidden(True)
					item.setDisabled(True)

	def _OnEraseBackground(self,event):
		#Workaround for windows background redraw flicker.
		pass

	def _OnSize(self,e):
		self._container.setSize(0, 0, self.GetSize().GetWidth(), self.GetSize().GetHeight())
		self._container.updateLayout()
		self.Refresh()

	def OnMouseDown(self,e):
		pass
	def OnMouseUp(self,e):
		pass
	def OnMouseMotion(self, e):
		pass
	def OnKeyChar(self, keyCode):
		pass
	def OnPaint(self, e):
		pass
	def OnKeyChar(self, keycode):
		pass

	def QueueRefresh(self):
		wx.CallAfter(self._queueRefresh)

	def _queueRefresh(self):
		self._refreshQueued = True

	def add(self, ctrl):
		if self._container is not None:
			self._container.add(ctrl)

class glGuiLayoutButtons(object):
	def __init__(self, parent):
		self._parent = parent
		self._parent._layout = self

	def update(self):
		bs = self._parent._base._buttonSize
		x0, y0, w, h = self._parent.getSize()
		gridSize = bs * 1.0
		for ctrl in self._parent._glGuiControlList:
			pos = ctrl._pos
			
			try:
				imageID = ctrl._imageID
			except:
				imageID = None
				
			if pos[0] < 0:
				x = w + pos[0] * gridSize - bs * 0.2
				if x < 660 + (pos[0] + 9) * gridSize and pos[0] != -1.11: #-1.11 is for the gcode slider. 
					x = 660 + (pos[0] + 9) * gridSize
			else:
				x = pos[0] * gridSize + bs * 0.2

			try:
				if ctrl._center == "bottom" or ctrl._center == "top":
					# x = float(w)/2 + (pos[0] * gridSize * 1.2) - gridSize/2
					x = float(w)/2 + (pos[0] * gridSize * 1.00) - gridSize/2
				if ctrl._center == "top-right":
					x = float(w) - gridSize
			except:
				#y = h + pos[1] * gridSize * 1.2 - bs * 0.2
				pass


				
			if pos[1] < 0:
				y = h + pos[1] * gridSize * 1.2 - bs * 0.2
				#gg = (pos[1] + 6.5) * 64
				if pos[1] == -1:
					pass
					# print "negative one"
			else:
				y = pos[1] * gridSize * 1.2 + bs * 0.2
			if pos[1] == 10:
				print "AHHA"
			try:
				if ctrl._center == "left" or ctrl._center == "right":
					y = float(h)/2 + (pos[1] * gridSize * 1.2) - gridSize
				if ctrl._center == "top" or ctrl._center == "top-right":
					y = bs + (pos[1] * gridSize * 1.2) - gridSize
			except:
				#y = h + pos[1] * gridSize * 1.2 - bs * 0.2
				pass

			
			ctrl.setSize(x, y, gridSize, gridSize)

	def getLayoutSize(self):
		_, _, w, h = self._parent.getSize()
		return w, h

class glGuiLayoutGrid(object):
	def __init__(self, parent):
		self._parent = parent
		self._parent._layout = self
		self._size = 0,0
		self._alignBottom = True

	def update(self):
		borderSize = self._parent._base._buttonSize * 0.2
		x0, y0, w, h = self._parent.getSize()
		x0 += borderSize
		y0 += borderSize
		widths = {}
		heights = {}
		for ctrl in self._parent._glGuiControlList:
			x, y = ctrl._pos
			w, h = ctrl.getMinSize()
			if not x in widths:
				widths[x] = w
			else:
				widths[x] = max(widths[x], w)
			if not y in heights:
				heights[y] = h
			else:
				heights[y] = max(heights[y], h)
		self._size = sum(widths.values()) + borderSize * 2, sum(heights.values()) + borderSize * 2
		if self._alignBottom:
			y0 -= self._size[1] - self._parent.getSize()[3]
			self._parent.setSize(x0 - borderSize, y0 - borderSize, self._size[0], self._size[1])
		for ctrl in self._parent._glGuiControlList:
			x, y = ctrl._pos
			x1 = x0
			y1 = y0
			for n in xrange(0, x):
				if not n in widths:
					widths[n] = 3
				x1 += widths[n]
			for n in xrange(0, y):
				if not n in heights:
					heights[n] = 3
				y1 += heights[n]
			ctrl.setSize(x1, y1, widths[x], heights[y])

	def getLayoutSize(self):
		return self._size

class glButton(glGuiControl):
	def __init__(self, parent, imageID, tooltipTitle, tooltip, pos, callback, Xnudge = 0, Ynudge = 0, size = None, center = "none", altHighlightColour = (0,0,0,0)):
		self._buttonSize = size
		self._hidden = False
		super(glButton, self).__init__(parent, pos)
		self._tooltip = tooltip
		self._tooltipTitle = tooltipTitle
		self._hoverHelp = ""
		self._parent = parent
		self._imageID = imageID
		self._callback = callback
		self._selected = False
		self._focus = False
		self._disabled = False
		self._showExpandArrow = False
		self._progressBar = None
		self._altTooltip = ''
		self._Xnudge = Xnudge
		self._Ynudge = Ynudge
		self._glDittoTexture = None
		self._center = center
		self._altHighlightColour = altHighlightColour

		self._tooltipNudgeX = 0
		self._tooltipNudgeY = 0
		
		self._highlight = True
		
		self._extraHitbox = None

		self._xBreakpoint = None
		
		self._tooltipTextTitle = tooltipText.tooltipText(self._Xnudge, self._Ynudge, self._tooltipTitle, "roboto-regular.ttf", 14, self.buttonTitleTextColour) #(43,182,115)
		self._tooltipText = tooltipText.tooltipText(0, 0, self._tooltip, "roboto-medium.ttf", 14, (self.buttonTooltipTextColour)) #(43,182,115) (39,167,105)

		self._hoverHelpText = tooltipText.tooltipText(self._Xnudge, self._Ynudge, self._hoverHelp, "roboto-regular.ttf", 14, self.buttonTitleTextColour) #(43,182,115)

	def getImageID(self):
		return int(self._imageID)
		
	def setImageID(self, value):
		self._imageID = value
		
	def setSelected(self, value):
		self._selected = value

	def setExpandArrow(self, value):
		self._showExpandArrow = value

	def setHidden(self, value):
		self._hidden = value

	def setDisabled(self, value):
		self._disabled = value

	def setProgressBar(self, value):
		self._progressBar = value

	def getProgressBar(self):
		return self._progressBar

	def setBottomText(self, value):
		self._altTooltip = value

	def getSelected(self):
		return self._selected

	def getMinSize(self):
		if self._hidden:
			return 0, 0
		if self._buttonSize is not None:
			return self._buttonSize, self._buttonSize
		return self._base._buttonSize, self._base._buttonSize

	def _getPixelPos(self):

		x0, y0, w, h = self.getSize()

		windowWidth = self._parent.GetSize()[0]
		if self._xBreakpoint != None and self._xBreakpoint < windowWidth:
			x0 = x0+self._xBreakpointNudge
		#print self.getSize()
		return self._Xnudge + x0 + w / 2,self._Ynudge + y0 + h / 2

	def setTooltipText(self, value):
		self._tooltipText._text = value

	def draw(self):
		if self._hidden:
			return
		try:
			if self._parent._progressBar < 0.01 and self._tooltipTitle == "ABORT":
				return
		except:
			pass
		cx = (self._imageID % 4) / 4
		cy = int(self._imageID / 4) / 4
		bs = self.getMinSize()[0]
		pos = self._getPixelPos()

		if self._imageID < 32:
			glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture)
		else:
			glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture2)

		#if self._disabled:
		#	glColor4ub(128,128,128,128)
		#else:
		#	glColor4ub(255,255,255,255)

		scale = 1

		self._tooltipTextTitle.makeText()
		self._tooltipText.makeText()

		# if self._selected:
		# 	glColor3ub(*self.buttonSelectedColour)

		if self._disabled:
			glColor4ub(255,255,255,100)
		elif self._focus and self._highlight:
			if self._altHighlightColour != (0,0,0,0):
				glColor4ub(*self._altHighlightColour)
			else:
				# glColor4ub(255,255,255,255)
				glColor3ub(*self.buttonHighlightColour)
		else:
			glColor4ub(*self.buttonUnselectedColour)

		opengl.glDrawTexturedQuad( pos[0]-bs*scale/2, pos[1]-bs*scale/2, bs*scale, bs*scale, self._imageID)


		if self._focus:
			if self._altHighlightColour != (0,0,0,0):
				glColor4ub(255,255,255,180)
				opengl.glDrawTexturedQuad(pos[0]-bs*scale/2, pos[1]-bs*scale/2, bs*scale, bs*scale-23, 11) #white square
			else:
				glColor4ub(255,255,255,150)
				opengl.glDrawTexturedQuad(pos[0]-bs*scale/2, pos[1]-bs*scale/2, bs*scale, bs*scale, 11) #white square

		glPushMatrix()
		glTranslatef(pos[0], pos[1], 0)
		glDisable(GL_TEXTURE_2D)
		glTranslatef(0, -0.55*bs*scale, 0)
		glPopMatrix()
		if self._center == "left":
			self._tooltipTextTitle._x = pos[0] +34 + self._tooltipNudgeX
			self._tooltipTextTitle._y = pos[1] +7 + self._tooltipNudgeY

			self._tooltipText._x = pos[0] +34
			self._tooltipText._y = pos[1] +22

			self._hoverHelpText._x = pos[0] +34 + self._tooltipNudgeX
			self._hoverHelpText._y = pos[1] +7 + self._tooltipNudgeY
		elif self._center == "bottom":
			length = len(str(self._tooltipTitle))
			try:
				self._tooltipTextTitle._x = pos[0] - (length/2)*13 + (1/length * 40) #TODO: calculate how long the word is
				self._tooltipTextTitle._y = pos[1] +52

				self._hoverHelpText._x = pos[0] - self._hoverHelpText._textSize[0]/2 + self._tooltipNudgeX
				self._hoverHelpText._y = pos[1] + self._tooltipNudgeY
			except:
				pass
		elif self._center == "right":
			self._tooltipTextTitle._x = pos[0] +34 + self._tooltipNudgeX
			self._tooltipTextTitle._y = pos[1] +7 + self._tooltipNudgeY

			self._tooltipText._x = pos[0] -270
			self._tooltipText._y = pos[1] +50

			self._hoverHelpText._x = pos[0] +34 + self._tooltipNudgeX
			self._hoverHelpText._y = pos[1] +7 + self._tooltipNudgeY
		elif self._center == "top":
			self._tooltipTextTitle._x = pos[0] - self._tooltipTextTitle._textSize[0]/2
			self._tooltipTextTitle._y = pos[1]

			self._tooltipText._x = pos[0] - self._tooltipText._textSize[0]/2
			self._tooltipText._y = pos[1] + bs/2

			self._hoverHelpText._x = pos[0] - self._hoverHelpText._textSize[0]/2 + self._tooltipNudgeX
			self._hoverHelpText._y = pos[1] + self._tooltipNudgeY
		else:
			self._hoverHelpText._x = pos[0] - self._hoverHelpText._textSize[0]/2 + self._tooltipNudgeX
			self._hoverHelpText._y = pos[1] + self._tooltipNudgeY
		glEnd()
		glDisable(GL_TEXTURE_2D)
		glPopMatrix()

		# if self._disabled:
		# 	glColor4ub(255,255,255,190)
		# 	opengl.glDrawTexturedQuad(pos[0]-bs*scale/2, pos[1]-bs*scale/2, bs*scale, bs*scale, 11) #white square

		if self._focus:
			if self._tooltipTitle != '':
				glBindTexture(GL_TEXTURE_2D, opengl.loadGLTexture3(self._tooltipTextTitle))
				# opengl.glDrawTexturedQuad(pos[0]-bs*scale/2, pos[1]-bs*scale/2, bs*scale, bs*scale, 10)
				self._tooltipTextTitle.displayText2()

		if self._tooltip != '':
			glBindTexture(GL_TEXTURE_2D, opengl.loadGLTexture3(self._tooltipText))
			self._tooltipText.displayText2()
		if self._hoverHelpText._text != "" and self._focus and not self._selected:
				glBindTexture(GL_TEXTURE_2D, opengl.loadGLTexture3(self._hoverHelpText))
				self._hoverHelpText.displayText2()
		glPopMatrix()
		progress = self._progressBar
		if progress is not None:
			glColor4ub(60,60,60,255)
			# opengl.glDrawQuad(pos[0]-bs/2, pos[1]+bs/2, bs, bs / 4)
			glColor4ub(255,255,255,100)
			opengl.glDrawQuad(pos[0]-bs/2, pos[1]-bs/2, (bs - 5) * progress + 1, bs )
		elif len(self._altTooltip) > 0:
			glPushMatrix()
			glTranslatef(pos[0], pos[1], 0)
			glTranslatef(0.6*bs*scale, 0, 0)

			glPushMatrix()
			glColor4ub(60,60,60,255)
			glTranslatef(-1, -1, 0)
			opengl.glDrawStringLeft(self._altTooltip)
			glTranslatef(0, 2, 0)
			opengl.glDrawStringLeft(self._altTooltip)
			glTranslatef(2, 0, 0)
			opengl.glDrawStringLeft(self._altTooltip)
			glTranslatef(0, -2, 0)
			opengl.glDrawStringLeft(self._altTooltip)
			glPopMatrix()

			glColor4ub(255,255,255,255)
			opengl.glDrawStringLeft(self._altTooltip)
			glPopMatrix()

	def _checkHit(self, x, y):
		if self._hidden or self._disabled:
			return False
		if self._parent._progressBar and not self._tooltipTitle == "ABORT":
			return False
		bs = self.getMinSize()[0]
		pos = self._getPixelPos()
		if self._extraHitbox:
			#print "new"
			return self._extraHitbox[0] <= x - pos[0] <= self._extraHitbox[1] and self._extraHitbox[2] <= y - pos[1] <= self._extraHitbox[3]
		
		return -bs * 0.5 <= x - pos[0] <= bs * 0.5 and -bs * 0.5 <= y - pos[1] <= bs * 0.5

	def OnMouseMotion(self, x, y):
		if self._checkHit(x, y):
			self._focus = True
			return True
		self._focus = False
		return False

	def OnMouseDown(self, x, y, button):
		if self._checkHit(x, y):
			self._callback(button)
			return True
		return False

class flexibleGlButton(glGuiControl):
	def __init__(self, parent, imageID, tooltipTitle, tooltip, pos, group, callback, Xnudge = 0, Ynudge = 0, size = None, center = "none", altHighlightColour = (0,0,0,0)):
		self._buttonSize = size
		self._hidden = False
		super(flexibleGlButton, self).__init__(parent, pos)
		self._tooltip = tooltip
		self._tooltipTitle = tooltipTitle
		self._hoverHelp = ""
		self._parent = parent
		self._imageID = imageID
		self._callback = callback
		self._selected = False
		self._focus = False
		self._disabled = False
		self._showExpandArrow = False
		self._progressBar = None
		self._altTooltip = ''
		self._Xnudge = Xnudge
		self._Ynudge = Ynudge
		self._glDittoTexture = None
		self._center = center
		self._altHighlightColour = altHighlightColour

		self._hoverOverlayColour = altHighlightColour #Temp variable for the hover overlay
		self._altHighlightImage = None

		self._group = group
		self._group.append(self)

		self._tooltipNudgeX = 0
		self._tooltipNudgeY = 0

		self._highlight = True

		self._extraHitbox = None
		self._xBreakpoint = None

		self._tooltipTextTitle = tooltipText.tooltipText(self._Xnudge, self._Ynudge, self._tooltipTitle, "roboto-regular.ttf", 14, self.buttonTitleTextColour) #(43,182,115)
		self._tooltipText = tooltipText.tooltipText(self._Xnudge, self._Ynudge, self._tooltip, "roboto-light.ttf", 15, ((88,89,91))) #(43,182,115) (39,167,105)
		self._tooltipTextSelected = tooltipText.tooltipText(self._Xnudge, self._Ynudge, self._tooltip, "roboto-light.ttf", 15, ((140,198,63))) #(43,182,115) (39,167,105)

		self._hoverHelpText = tooltipText.tooltipText(self._Xnudge, self._Ynudge, self._hoverHelp, "roboto-regular.ttf", 14, self.buttonTitleTextColour) #(43,182,115)


	def getImageID(self):
		return int(self._imageID)

	def setImageID(self, value):
		self._imageID = value

	def setSelected(self, value):
		self._selected = value

	def setExpandArrow(self, value):
		self._showExpandArrow = value

	def setHidden(self, value):
		self._hidden = value

	def setDisabled(self, value):
		self._disabled = value

	def setProgressBar(self, value):
		self._progressBar = value

	def getProgressBar(self):
		return self._progressBar

	def setBottomText(self, value):
		self._altTooltip = value

	def getSelected(self):
		return self._selected

	def setTooltipText(self, text):
		self._tooltipText._text = text

	def setTooltipColour(self, colour):
		self._tooltipText._colour = colour
		self._tooltipText.makeText(True)

	def setTooltipFont(self, font):
		self._tooltipText._font = font
		self._tooltipText.makeText(True)

	def setTooltipFontSize(self, size):
		self._tooltipText._fontsize = size
		self._tooltipText.makeText(True)

	def setTextAlignment(self, alignment):
		self._tooltipText.alignment = alignment

	def getMinSize(self):
		if self._hidden:
			return 0, 0
		if self._buttonSize is not None:
			return self._buttonSize
		return self._base._buttonSize, self._base._buttonSize

	def _getPixelPos(self):
		x0, y0, w, h = self.getSize()
		windowWidth = self._parent.GetSize()[0]
		if self._xBreakpoint != None and self._xBreakpoint < windowWidth:
			x0 = x0+self._xBreakpointNudge
		#print self.getSize()
		return self._Xnudge + x0 + w / 2,self._Ynudge + y0 + h / 2

	def draw(self):
		if self._hidden:
			return
		try:
			if self._parent._progressBar < 0.01 and self._tooltipTitle == "ABORT":
				return
		except:
			pass
		cx = (self._imageID % 4) / 4
		cy = int(self._imageID / 4) / 4
		buttonWidth = self.getMinSize()[0]
		buttonHeight = self.getMinSize()[1]
		pos = self._getPixelPos()

		imageToUse = self._imageID

		if self._altHighlightImage != None and self._focus:
			imageToUse = self._altHighlightImage

		if imageToUse < 32:
			glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture)
		else:
			glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture2)

		#if self._disabled:
		#	glColor4ub(128,128,128,128)
		#else:
		#	glColor4ub(255,255,255,255)

		scale = 1

		# if self._selected:
		# 	glColor3ub(*self.buttonSelectedColour)



		# elif self._focus and self._highlight:
		# 	if self._altHighlightColour != (0,0,0,0):
		# 		glColor4ub(*self._altHighlightColour)
		# 	else:
		# 		# glColor4ub(255,255,255,255)
		# 		glColor3ub(*self.buttonHighlightColour)
		# else:
		# 	glColor4ub(*self.buttonUnselectedColour)

		if self._focus and self._highlight and self._altHighlightColour is not None:
			if self._altHighlightColour != (0,0,0,0):
				glColor4ub(*self._altHighlightColour)
			else:
				# glColor4ub(255,255,255,255)
				glColor3ub(*self.buttonHighlightColour)
		else:
			glColor4ub(*self.buttonUnselectedColour)

		if self._disabled and self._progressBar == None:
			glColor4ub(255,255,255,100)
		#opengl.glDrawTexturedQuad(self._Xnudge+pos[0]-bs*scale/2, self._Ynudge + pos[1]-bs*scale/2, bs*scale, bs*scale, 0)
		# opengl.glDrawTexturedQuad(self._Xnudge+pos[0]-bs*scale/2, self._Ynudge + pos[1]-bs*scale/2, bs*scale, bs*scale, self._imageID)
		opengl.glDrawTexturedQuad( pos[0]-buttonWidth*scale/2, pos[1]-buttonHeight*scale/2, buttonWidth*scale, buttonHeight*scale, imageToUse)

		if self._focus and self._hoverOverlayColour is not None:
			if self._hoverOverlayColour != (0,0,0,0):
				glColor4ub(255,255,255,80)
				opengl.glDrawTexturedQuad(pos[0]-buttonWidth*scale/2, pos[1]-buttonHeight*scale/2, buttonWidth*scale, buttonHeight*scale, 11) #white square
			else:
				glColor4ub(255,255,255,200)
				opengl.glDrawTexturedQuad(pos[0]-buttonWidth*scale/2-1, pos[1]-buttonHeight*scale/2, buttonWidth*scale, buttonHeight*scale, 11) #white square

		glPushMatrix()
		glTranslatef(pos[0], pos[1], 0)
		glDisable(GL_TEXTURE_2D)
		glTranslatef(0, -0.55*buttonHeight*scale, 0)
		glPopMatrix()

		if self._center == "left":
			self._tooltipTextTitle._x = pos[0] +34 + self._tooltipNudgeX
			self._tooltipTextTitle._y = pos[1] +7 + self._tooltipNudgeY

			self._tooltipText._x = pos[0] +34
			self._tooltipText._y = pos[1] +22

			self._hoverHelpText._x = pos[0] +34 + self._tooltipNudgeX
			self._hoverHelpText._y = pos[1] +7 + self._tooltipNudgeY

		elif self._center == "bottom":
			self._tooltipTextTitle._x = pos[0] - self._tooltipTextTitle._textSize[0]/2 + self._tooltipNudgeX
			self._tooltipTextTitle._y = pos[1] + self._tooltipNudgeY

			self._hoverHelpText._x = pos[0] - self._hoverHelpText._textSize[0]/2 + self._tooltipNudgeX
			self._hoverHelpText._y = pos[1] + self._tooltipNudgeY

			self._tooltipText._x = pos[0] - self._tooltipText._textSize[0]/2
			self._tooltipText._y = pos[1] + buttonHeight/2.5

			self._tooltipTextSelected._x = pos[0] - self._tooltipTextSelected._textSize[0]/2
			self._tooltipTextSelected._y = pos[1] + buttonHeight/2.5
		elif self._center == "right":
			self._tooltipTextTitle._x = pos[0] +34 + self._tooltipNudgeX
			self._tooltipTextTitle._y = pos[1] +7 + self._tooltipNudgeY

			self._hoverHelpText._x = pos[0] +34 + self._tooltipNudgeX
			self._hoverHelpText._y = pos[1] +7 + self._tooltipNudgeY

			self._tooltipText._x = pos[0] -270
			self._tooltipText._y = pos[1] +50
		elif self._center == "top":
			self._tooltipTextTitle._x = pos[0] - self._tooltipTextTitle._textSize[0]/2 + self._tooltipNudgeX
			self._tooltipTextTitle._y = pos[1] + self._tooltipNudgeY

			self._hoverHelpText._x = pos[0] - self._hoverHelpText._textSize[0]/2 + self._tooltipNudgeX
			self._hoverHelpText._y = pos[1] + self._tooltipNudgeY

			self._tooltipText._x = pos[0] - self._tooltipText._textSize[0]/2
			self._tooltipText._y = pos[1] + buttonHeight/2.5

			self._tooltipTextSelected._x = pos[0] - self._tooltipTextSelected._textSize[0]/2
			self._tooltipTextSelected._y = pos[1] + buttonHeight/2.5
		elif self._center == "top-right":
			self._hoverHelpText._x = pos[0] - self._hoverHelpText._textSize[0]/2 + self._tooltipNudgeX
			self._hoverHelpText._y = pos[1] + self._tooltipNudgeY

			self._tooltipText._x = pos[0] - self._tooltipText._textSize[0]/2 + self._tooltipNudgeX
			self._tooltipText._y = pos[1] + buttonHeight/2.5 + self._tooltipNudgeY

			self._tooltipTextSelected._x = pos[0] - self._tooltipTextSelected._textSize[0]/2 + self._tooltipNudgeX
			self._tooltipTextSelected._y = pos[1] + buttonHeight/2.5  + self._tooltipNudgeY


		glEnd()
		glDisable(GL_TEXTURE_2D)
		glPopMatrix()
		if self._focus:
			if self._tooltipTitle != '':
				glBindTexture(GL_TEXTURE_2D, opengl.loadGLTexture3(self._tooltipTextTitle))
				opengl.glDrawTexturedQuad(pos[0]-buttonWidth*scale/2, pos[1]-buttonHeight*scale/2, buttonWidth*scale, buttonHeight*scale, 10)
				self._tooltipTextTitle.displayText2()
		if self._tooltip != '':
			if not self._selected:
				glBindTexture(GL_TEXTURE_2D, opengl.loadGLTexture3(self._tooltipText))
				self._tooltipText.displayText2()
			else:
				glBindTexture(GL_TEXTURE_2D, opengl.loadGLTexture3(self._tooltipTextSelected))
				self._tooltipTextSelected.displayText2()
		if self._hoverHelpText._text != "" and self._focus:
				glBindTexture(GL_TEXTURE_2D, opengl.loadGLTexture3(self._hoverHelpText))
				self._hoverHelpText.displayText2()

		glPopMatrix()
		# progress = self._progressBar
		# if progress is not None:
		# 	glColor4ub(60,60,60,255)
		# 	opengl.glDrawQuad(pos[0]-buttonWidth/2, pos[1]+buttonHeight/2, buttonWidth, buttonHeight / 4)
		# 	glColor4ub(255,255,255,255)
		# 	opengl.glDrawQuad(pos[0]-buttonWidth/2+2, pos[1]+buttonHeight/2+2, (buttonWidth - 5) * progress + 1, buttonHeight / 4 - 4)

		progress = self._progressBar
		if progress is not None:
			# glColor4ub(60,60,60,255)
			# opengl.glDrawQuad(pos[0]-bs/2, pos[1]+bs/2, bs, bs / 4)
			glColor4ub(255,255,255,100)
			opengl.glDrawQuad(pos[0]-buttonWidth/2, pos[1]-buttonHeight/2, (buttonWidth - 5) * progress + 1, buttonHeight )
		elif len(self._altTooltip) > 0:
			glPushMatrix()
			glTranslatef(pos[0], pos[1], 0)
			glTranslatef(0.6*buttonWidth*scale, 0, 0)

			glPushMatrix()
			glColor4ub(60,60,60,255)
			glTranslatef(-1, -1, 0)
			opengl.glDrawStringLeft(self._altTooltip)
			glTranslatef(0, 2, 0)
			opengl.glDrawStringLeft(self._altTooltip)
			glTranslatef(2, 0, 0)
			opengl.glDrawStringLeft(self._altTooltip)
			glTranslatef(0, -2, 0)
			opengl.glDrawStringLeft(self._altTooltip)
			glPopMatrix()

			glColor4ub(255,255,255,255)
			opengl.glDrawStringLeft(self._altTooltip)
			glPopMatrix()
		glColor4ub(255,255,255,255)

	def _checkHit(self, x, y):
		if self._hidden or self._disabled:
			return False
		if self._parent._progressBar and not self._tooltipTitle == "ABORT":
			return False
		buttonWidth = self.getMinSize()[0]
		buttonHeight = self.getMinSize()[1]
		pos = self._getPixelPos()
		if self._extraHitbox:
			#print "new"

			return self._extraHitbox[0] <= x - pos[0] <= self._extraHitbox[1] and self._extraHitbox[2] <= y - pos[1] <= self._extraHitbox[3]

		return -buttonWidth * 0.5 <= x - pos[0] <= buttonWidth * 0.5 and -buttonHeight * 0.5 <= y - pos[1] <= buttonHeight * 0.5

	def OnMouseMotion(self, x, y):
		if self._checkHit(x, y):
			self._focus = True
			return True
		self._focus = False
		return False

	def OnMouseDown(self, x, y, button):
		if self._checkHit(x, y):
			self._callback(button)
			return True
		return False

class flexibleGLTextLabel(flexibleGlButton):
	def __init__(self, parent, imageID, tooltip, pos, group, xNudge, yNudge, size, center, font="roboto-light.ttf", fontColour=(88,89,91), fontSize=15):
		super(flexibleGLTextLabel, self).__init__(parent, imageID, "", tooltip, pos, group, None, xNudge, yNudge, size, center)
		self._disabled = True

		self.setTooltipFont(font)
		self.setTooltipFontSize(fontSize)
		self.setTooltipColour(fontColour)


	def draw(self):
		if self._hidden:
			return
		try:
			if self._parent._progressBar < 0.01 and self._tooltipTitle == "ABORT":
				return
		except:
			pass
		cx = (self._imageID % 4) / 4
		cy = int(self._imageID / 4) / 4
		buttonWidth = self.getMinSize()[0]
		buttonHeight = self.getMinSize()[1]
		pos = self._getPixelPos()

		if self._imageID < 32:
			glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture)
		else:
			glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture2)

		#if self._disabled:
		#	glColor4ub(128,128,128,128)
		#else:
		#	glColor4ub(255,255,255,255)

		scale = 1

		# if self._selected:
		# 	glColor3ub(*self.buttonSelectedColour)
		if self._focus and self._highlight:
			glColor3ub(*self.buttonHighlightColour)
		else:
			glColor4ub(*self.buttonUnselectedColour)
		#opengl.glDrawTexturedQuad(self._Xnudge+pos[0]-bs*scale/2, self._Ynudge + pos[1]-bs*scale/2, bs*scale, bs*scale, 0)
		# opengl.glDrawTexturedQuad(self._Xnudge+pos[0]-bs*scale/2, self._Ynudge + pos[1]-bs*scale/2, bs*scale, bs*scale, self._imageID)
		opengl.glDrawTexturedQuad( pos[0]-buttonWidth*scale/2, pos[1]-buttonHeight*scale/2, buttonWidth*scale, buttonHeight*scale, self._imageID)

		glPushMatrix()
		glTranslatef(pos[0], pos[1], 0)
		glDisable(GL_TEXTURE_2D)
		glTranslatef(0, -0.55*buttonHeight*scale, 0)
		glPopMatrix()

		if self._center == "left":
			self._tooltipTextTitle._x = pos[0] +34 + self._tooltipNudgeX
			self._tooltipTextTitle._y = pos[1] +7 + self._tooltipNudgeY

			self._tooltipText._x = pos[0] +34
			self._tooltipText._y = pos[1] +22
		elif self._center == "bottom":
			self._tooltipTextTitle._x = pos[0] - self._tooltipTextTitle._textSize[0]/2
			self._tooltipTextTitle._y = pos[1]
			self._tooltipText._x = pos[0] - self._tooltipText._textSize[0]/2
			self._tooltipText._y = pos[1] + buttonHeight/2.5
			self._tooltipTextSelected._x = pos[0] - self._tooltipTextSelected._textSize[0]/2
			self._tooltipTextSelected._y = pos[1] + buttonHeight/2.5
		elif self._center == "right":
			self._tooltipTextTitle._x = pos[0] +34 + self._tooltipNudgeX
			self._tooltipTextTitle._y = pos[1] +7 + self._tooltipNudgeY

			self._tooltipText._x = pos[0] -270
			self._tooltipText._y = pos[1] +50
		elif self._center == "top":
			self._tooltipTextTitle._x = pos[0] - self._tooltipTextTitle._textSize[0]/2
			self._tooltipTextTitle._y = pos[1]
			self._tooltipText._x = pos[0] - self._tooltipText._textSize[0]/2
			self._tooltipText._y = pos[1] + buttonHeight/2.5
			self._tooltipTextSelected._x = pos[0] - self._tooltipTextSelected._textSize[0]/2
			self._tooltipTextSelected._y = pos[1] + buttonHeight/2.5

		glEnd()
		glDisable(GL_TEXTURE_2D)
		glPopMatrix()

		if self._tooltip != '':
			if not self._selected:
				glBindTexture(GL_TEXTURE_2D, opengl.loadGLTexture3(self._tooltipText))
				self._tooltipText.displayText2()
			else:
				glBindTexture(GL_TEXTURE_2D, opengl.loadGLTexture3(self._tooltipTextSelected))
				self._tooltipTextSelected.displayText2()

		glPopMatrix()

class glRadioButton(glButton):
	def __init__(self, parent, imageID, tooltipTitle, tooltip, pos, group, callback, xNudge, yNudge, size, scaleModifier, center):
		super(glRadioButton, self).__init__(parent, imageID, tooltipTitle, tooltip, pos, self._onRadioSelect, xNudge, yNudge, size, center)
		self._group = group
		self._radioCallback = callback
		self._group.append(self)
		self._center = center
		self._scaleModifier = scaleModifier

	def setSelected(self, value):
		self._selected = value

	def _onRadioSelect(self, button):
		self._base._focus = None
		for ctrl in self._group:
			if ctrl != self:
				ctrl.setSelected(False)
		if self.getSelected():
			self.setSelected(False)
		else:
			self.setSelected(True)
		self._radioCallback(button)
		
	def _checkHit(self, x, y):
		if self._hidden or self._disabled or self._parent._progressBar:
			return False
		bs = self.getMinSize()[0]*self._scaleModifier
		pos = self._getPixelPos()
		return -bs * 0.5 <= x - pos[0] <= bs * 0.5 and -bs * 0.5 <= y - pos[1] <= bs * 0.5

class new_age_glRadioButton(glButton):
	# top level menu radio button
	# self, parent, imageID, tooltipTitle, tooltip, pos, callback, Xnudge = 0, Ynudge = 0, size = None, center = "none", useAltHighlightColour = False
	def __init__(self, parent, imageID, tooltipTitle, tooltip, pos, group, callback, xNudge, yNudge, size, center, altHighlightColour=(0,0,0,0)):
		super(new_age_glRadioButton, self).__init__(parent, imageID, tooltipTitle, tooltip, pos, self._onRadioSelect, xNudge, yNudge, size, center, altHighlightColour)
		self._group = group
		self._radioCallback = callback
		self._group.append(self)
		self._center = center
		self._dependantGroup = []
		self._imageID = imageID

	def setSelected(self, value):
		self._selected = value
		for ctrl in self._dependantGroup:
			ctrl.setHidden(not value)
			try:
				if ctrl.advancedOnly and profile.getPreference('show_advanced') != 'True':
					ctrl.setHidden(True)
			except:
				pass
	def setDependantGroup(self, group):
		self._dependantGroup = group

	def _onRadioSelect(self, button):
		self._base._focus = None
		for ctrl in self._group:
			if ctrl != self:
				ctrl.setSelected(False)

		if self.getSelected():
			self.setSelected(False)
		else:
			self.setSelected(True)
		self._radioCallback(button)

class new_age_flexibleGlRadioButton(flexibleGlButton):
	# setting radio button
	def __init__(self, parent, imageID, tooltipTitle, tooltip, pos, group, callback, xNudge, yNudge, size, center, altHighlightColour=(0,0,0,0)):
		super(new_age_flexibleGlRadioButton, self).__init__(parent, imageID, tooltipTitle, tooltip, pos, group, self._onRadioSelect, xNudge, yNudge, size, center, altHighlightColour)
		self._group = group
		self._radioCallback = callback
		self._center = center
		self._dependantGroup = []
		self._imageID = imageID

	def setSelected(self, value):
		self._selected = value
		for ctrl in self._dependantGroup:
			ctrl.setHidden(not value)
			try:
				if ctrl.advancedOnly and profile.getPreference('show_advanced') != 'True':
					ctrl.setHidden(True)
			except:
				pass

	def setDependantGroup(self, group):
		self._dependantGroup = group

	def _onRadioSelect(self, button):
		self._base._focus = None
		for ctrl in self._group:
			if ctrl != self:
				ctrl.setSelected(False)

		# if self.getSelected():
		# 	self.setSelected(False)
		# else:
			self.setSelected(True)
		self._radioCallback(button)

class glComboButton(glButton):
	def __init__(self, parent, tooltipTitle, tooltip, imageIDs, tooltips, pos, callback):
		super(glComboButton, self).__init__(parent, imageIDs[0], tooltipTitle, tooltip, pos, self._onComboOpenSelect)
		self._imageIDs = imageIDs
		self._tooltips = tooltips
		self._comboCallback = callback
		self._selection = 0

	def _onComboOpenSelect(self, button):
		if self.hasFocus():
			self._base._focus = None
		else:
			self._base._focus = self

	def draw(self):
		if self._hidden:
			return
		self._selected = self.hasFocus()
		super(glComboButton, self).draw()

		if self._buttonSize != None:
			bs = self._buttonSize /2
		else:
			bs = self._base._buttonSize / 2
		pos = self._getPixelPos()

		if not self._selected:
			return

		glPushMatrix()
		glTranslatef(pos[0]+bs*0.5, pos[1] + bs*0.5, 0)
		glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture)
		for n in xrange(0, len(self._imageIDs)):
			glTranslatef(0, bs, 0)
			glColor4ub(255,255,0,255)
			opengl.glDrawTexturedQuad(-0.5*bs,-0.5*bs,bs,bs, 0)
			opengl.glDrawTexturedQuad(-0.5*bs,-0.5*bs,bs,bs, self._imageIDs[n])
			glDisable(GL_TEXTURE_2D)

			glPushMatrix()
			glTranslatef(-0.55*bs, 0.1*bs, 0)

			glPushMatrix()
			glColor4ub(60,60,60,255)
			glTranslatef(-1, -1, 0)
			opengl.glDrawStringRight(self._tooltips[n])
			glTranslatef(0, 2, 0)
			opengl.glDrawStringRight(self._tooltips[n])
			glTranslatef(2, 0, 0)
			opengl.glDrawStringRight(self._tooltips[n])
			glTranslatef(0, -2, 0)
			opengl.glDrawStringRight(self._tooltips[n])
			glPopMatrix()

			glColor4ub(255,255,255,255)
			opengl.glDrawStringRight(self._tooltips[n])
			glPopMatrix()
		glPopMatrix()

	def getValue(self):
		return self._selection

	def setValue(self, value):
		self._selection = value
		self._imageID = self._imageIDs[self._selection]
		self._comboCallback()

	def OnMouseDown(self, x, y, button):
		if self._hidden or self._disabled:
			return False
		if self.hasFocus():
			bs = self._base._buttonSize / 2
			pos = self._getPixelPos()
			if 0 <= x - pos[0] <= bs and 0 <= y - pos[1] - bs <= bs * len(self._imageIDs):
				self._selection = int((y - pos[1] - bs) / bs)
				self._imageID = self._imageIDs[self._selection]
				self._base._focus = None
				self._comboCallback()
				return True
		return super(glComboButton, self).OnMouseDown(x, y, button)

class glFrame(glGuiContainer):
	def __init__(self, parent, pos):
		super(glFrame, self).__init__(parent, pos)
		self._selected = False
		self._focus = False
		self._hidden = False

	def setSelected(self, value):
		self._selected = value

	def setHidden(self, value):
		self._hidden = value
		for child in self._glGuiControlList:
			if self._base._focus == child:
				self._base._focus = None

	def getSelected(self):
		return self._selected

	def getMinSize(self):
		return self._base._buttonSize, self._base._buttonSize

	def _getPixelPos(self):
		x0, y0, w, h = self.getSize()
		return x0, y0

	def draw(self):
		if self._hidden:
			return

		bs = self._parent._buttonSize
		pos = self._getPixelPos()

		size = self._layout.getLayoutSize()
		#glColor4ub(0,0,0,200)
		#opengl.glDrawStretchedQuad(pos[0], pos[1], size[0], size[1], bs*0.75, 0)
		#Draw the controls on the frame
		super(glFrame, self).draw()

	def _checkHit(self, x, y):
		if self._hidden:
			return False
		pos = self._getPixelPos()
		w, h = self._layout.getLayoutSize()
		#print w,h
		return 0 <= x - pos[0] <= w and 0 <= y - pos[1] <= h

	def OnMouseMotion(self, x, y):
		#super(glFrame, self).OnMouseMotion(x, y)
		if self._checkHit(x, y):
			self._focus = True
			return True
		self._focus = False
		return False

	def OnMouseDown(self, x, y, button):
		if self._checkHit(x, y):
			super(glFrame, self).OnMouseDown(x, y, button)
			return True
		return False

class glNotification(glFrame):
	def __init__(self, parent, pos):
		self._anim = None
		super(glNotification, self).__init__(parent, pos)
		glGuiLayoutGrid(self)._alignBottom = False
		self._label = glLabel(self, "Notification", (0, 0))
		self._buttonEject = glButton(self, 31, "Eject", '', (1, 0), self.onEject, 25)
		self._button = glButton(self, 30, "", '', (2, 0), self.onClose, 25)
		self._padding = glLabel(self, "", (0, 1))
		self.setHidden(True)

	def setSize(self, x, y, w, h):
		w, h = self._layout.getLayoutSize()
		baseSize = self._base.GetSizeTuple()
		if self._anim is not None:
			super(glNotification, self).setSize(baseSize[0] / 2 - w / 2, baseSize[1] - self._anim.getPosition() - self._base._buttonSize * 0.2, 1, 1)
		else:
			super(glNotification, self).setSize(baseSize[0] / 2 - w / 2, baseSize[1] - self._base._buttonSize * 0.2, 1, 1)

	def draw(self):
		self.setSize(0,0,0,0)
		self.updateLayout()
		super(glNotification, self).draw()

	def message(self, text, ejectCallback = None):
		self._anim = animation(self._base, -20, 25, 1)
		self.setHidden(False)
		self._label.setLabel(text)
		self._buttonEject.setHidden(ejectCallback is None)
		self._ejectCallback = ejectCallback
		self._base._queueRefresh()
		self.updateLayout()

	def onEject(self, button):
		self.onClose(button)
		self._ejectCallback()

	def onClose(self, button):
		if self._anim is not None:
			self._anim = animation(self._base, self._anim.getPosition(), -20, 1)
		else:
			self._anim = animation(self._base, 25, -20, 1)

class glLabel(glGuiControl):
	def __init__(self, parent, label, pos, size = 11, colour = (0,0,0,255)):
		self._label = label
		super(glLabel, self).__init__(parent, pos)
		self._center = None
		self._tooltipText = tooltipText.tooltipText(200, 200, self._label, "Roboto-Regular.ttf", size, colour) #(139,197,63)) #(43,182,115)
		self._hidden = False
	def setLabel(self, label):
		self._label = label
		
	def setHidden(self, value):
		self._hidden = value
		
	def getMinSize(self):
		w, h = opengl.glGetStringSize(self._label)
		return w + 10, h + 4

	def _getPixelPos(self):
		x0, y0, w, h = self.getSize()
		return x0, y0

	def draw(self):
		if self._hidden:
			return
		x, y, w, h = self.getSize()
		
		glPushMatrix()
		glTranslatef(x, y, 0)

		glColor4ub(0,0,0,0)
		glBegin(GL_QUADS)
		glTexCoord2f(1, 0)
		glVertex2f( w, 0)
		glTexCoord2f(0, 0)
		glVertex2f( 0, 0)
		glTexCoord2f(0, 1)
		glVertex2f( 0, h)
		glTexCoord2f(1, 1)
		glVertex2f( w, h)
		glEnd()
		glPopMatrix()
		
		stringLength = opengl.glGetStringSize(self._label[0:len(self._label)])[0]
		adjust = stringLength/2
		
		self._tooltipText._x = x - adjust
		self._tooltipText._y = y + h
		self._tooltipText._text = self._label
		
		#self._tooltipText.makeText()		
		#self._tooltipText.displayText()
		if self._label != '':
			glBindTexture(GL_TEXTURE_2D, opengl.loadGLTexture3(self._tooltipText))
			self._tooltipText.displayText2()
		
		#glTranslate(5, h - 5, 0)
		glColor4ub(0,0,0,255)
		#opengl.glDrawStringLeft(self._label)
		glPopMatrix()

	def _checkHit(self, x, y):
		return False

	def OnMouseMotion(self, x, y):
		return False

	def OnMouseDown(self, x, y, button):
		return False

class glNumberCtrl(glGuiControl):
	def __init__(self, parent, imageID, value, pos, callback, isPercent = False):
		self._callback = callback
		self._value = str(value)
		self._selectPos = 0
		self._maxLen = 5
		self._inCallback = False
		self._center = "bottom"
		self._isPercent = isPercent
		self._hidden = False
		self._imageID = imageID
		self._focus = False
		super(glNumberCtrl, self).__init__(parent, pos)

		self._tooltipText = tooltipText.tooltipText(0, 0, self._value, "roboto-light.ttf", 16, (88,89,91))
		self._tooltipTextHighlighted = tooltipText.tooltipText(0, 0, self._value, "roboto-regular.ttf", 16, (88,89,91))

	def setHidden(self, value):
		self._hidden = value

	def setValue(self, value):
		if self._inCallback:
			return
		self._value = str(value)

	def getMinSize(self):
		w, h = opengl.glGetStringSize("VALUES")
		return w + 4, h + 4

	def _getPixelPos(self):
		x0, y0, w, h = self.getSize()
		w, h = opengl.glGetStringSize("VALUES")
		# w -= 25
		# h += 10
		return x0, y0

	def draw(self):
		#if not self._parent.scaleToolButton.getSelected():
		#	return
		if self._hidden:
			return
		x, y, w, h = self.getSize()
		w, h = opengl.glGetStringSize("VALUES")
		# w -= 25
		# h += 10

		bs = self.getMinSize()[0]
		pos = self._getPixelPos()
		scale = 1.2

		if self._imageID < 32:
			glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture)
		else:
			glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture2)
		glColor4ub(255,255,255,255)
		opengl.glDrawTexturedQuad( pos[0]-bs*scale/2, pos[1]-bs*scale/2, bs*scale, bs*scale, self._imageID)
		#x+=10
		stringLength = opengl.glGetStringSize(self._value[0:len(self._value)])[0]
		adjust = stringLength / 2.0
		#if self._isPercent:
			#adjust = (3 - len(self._value)) * 5
		#	adjust = stringLength / 2.0
		#else:
		#	adjust = (4 - len(self._value)) * 7
		x -= adjust
		glPushMatrix()
		#glTranslatef(x, y, 0)
		# if self._focus:
		# 	glColor4ub(255,255,255,180)
		# 	glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture)
		# 	opengl.glDrawTexturedQuad(pos[0]-bs*scale/2, pos[1]-bs*scale/2, bs*scale, bs*scale, 11) #white square

		if self.hasFocus():
			glColor4ub(220,220,220,0)
			glBegin(GL_QUADS)
			glTexCoord2f(1, 0)
			glVertex2f( w, 0)
			glTexCoord2f(0, 0)
			glVertex2f( 0, 0)
			glTexCoord2f(0, 1)
			glVertex2f( 0, h-1)
			glTexCoord2f(1, 1)
			glVertex2f( w, h-1)
			glEnd()
		else:
			glColor4ub(200,200,200,150)

		glTranslate(5, h - 5, 0)
		glColor4ub(0,0,0,255)


		self._tooltipText._y = y
		self._tooltipText._text = self._value


		if self._isPercent:
			self._tooltipText._text += "%"
			nudge = 10
		else:
			self._tooltipText._text += " mm"
			nudge = 20
		self._tooltipText._x = x - nudge

		self._tooltipTextHighlighted._x = self._tooltipText._x
		self._tooltipTextHighlighted._y = self._tooltipText._y
		self._tooltipTextHighlighted._text = self._tooltipText._text

		if self._value != '':
			if self._focus or self.hasFocus():
				glBindTexture(GL_TEXTURE_2D, opengl.loadGLTexture3(self._tooltipTextHighlighted))
				self._tooltipTextHighlighted.displayText2()
			else:
				glBindTexture(GL_TEXTURE_2D, opengl.loadGLTexture3(self._tooltipText))
				self._tooltipText.displayText2()

		glColor4ub(0,0,0,255)
		if self.hasFocus():
			glTranslate(x+((opengl.glGetStringSize(self._value[0:self._selectPos])[0] - 1))-nudge, y-6, 0)
			opengl.glDrawStringLeft('|')
		glPopMatrix()

	def _checkHit(self, x, y):
		if self._parent._progressBar:
			return False
		x1, y1, w, h = self.getSize()
		w, h = opengl.glGetStringSize("VALUES")
		x1 -= 45
		y1 -= 20
		w += 25
		h += 25
		return 0 <= x - x1 <= w and 0 <= y - y1 <= h

	def OnMouseMotion(self, x, y):
		if self._checkHit(x, y):
			self._focus = True
			return True
		self._focus = False
		return False

	def OnMouseDown(self, x, y, button):
		if self._checkHit(x, y):
			self.setFocus()
			return True
		return False

	def OnKeyChar(self, c):
		self._inCallback = True
		if c == wx.WXK_LEFT:
			self._selectPos -= 1
			self._selectPos = max(0, self._selectPos)
		if c == wx.WXK_RIGHT:
			self._selectPos += 1
			self._selectPos = min(self._selectPos, len(self._value))
		if c == wx.WXK_UP:
			try:
				value = float(self._value)
			except:
				pass
			else:
				value += 1
				self._value = str(value)
				self._callback(self._value)
		if c == wx.WXK_DOWN:
			try:
				value = float(self._value)
			except:
				pass
			else:
				value -= 1
				if value > 0:
					self._value = str(value)
					self._callback(self._value)
		if c == wx.WXK_BACK and self._selectPos > 0:
			self._value = self._value[0:self._selectPos - 1] + self._value[self._selectPos:]
			self._selectPos -= 1
			self._callback(self._value)
		if c == wx.WXK_DELETE:
			self._value = self._value[0:self._selectPos] + self._value[self._selectPos + 1:]
			self._callback(self._value)
		if c == wx.WXK_TAB or c == wx.WXK_NUMPAD_ENTER or c == wx.WXK_RETURN:
			if wx.GetKeyState(wx.WXK_SHIFT):
				pass
				#self.focusPrevious()
			else:
				pass
				#self.focusNext()
		if (ord('0') <= c <= ord('9') or c == ord('.')) and len(self._value) < self._maxLen:
			self._value = self._value[0:self._selectPos] + chr(c) + self._value[self._selectPos:]
			self._selectPos += 1
			self._callback(self._value)
		self._inCallback = False

	def setFocus(self):
		self._base._focus = self
		self._selectPos = len(self._value)
		return True

class glCheckbox(glGuiControl):
	def __init__(self, parent, value, pos, callback):
		self._callback = callback
		self._value = value
		self._selectPos = 0
		self._maxLen = 6
		self._inCallback = False
		super(glCheckbox, self).__init__(parent, pos)

	def setValue(self, value):
		if self._inCallback:
			return
		self._value = str(value)

	def getValue(self):
		return self._value

	def getMinSize(self):
		return 20, 20

	def _getPixelPos(self):
		x0, y0, w, h = self.getSize()
		return x0, y0

	def draw(self):
		x, y, w, h = self.getSize()

		glPushMatrix()
		glTranslatef(x, y, 0)

		glColor4ub(0,0,0,255)
		
		if self._value:
			opengl.glDrawTexturedQuad(w-h/2,0, h, h, 28)
		else:
			opengl.glDrawTexturedQuad(w/2-h/2,0, h, h, 29)
		glDisable(GL_TEXTURE_2D)
		glPopMatrix()

	def _checkHit(self, x, y):
		x1, y1, w, h = self.getSize()
		return 0 <= x - x1 <= w and 0 <= y - y1 <= h

	def OnMouseMotion(self, x, y):
		return False

	def OnMouseDown(self, x, y, button):
		if self._checkHit(x, y):
			self._value = not self._value
			return True
		return False

class glSlider(glGuiControl):
	def __init__(self, parent, value, minValue, maxValue, pos, callback):
		super(glSlider, self).__init__(parent, pos)
		self._callback = callback
		self._focus = False
		self._hidden = False
		self._value = value
		self._minValue = minValue
		self._maxValue = maxValue
		self._parent = parent

	def setValue(self, value):
		self._value = value

	def getValue(self):
		if self._value < self._minValue:
			return self._minValue
		if self._value > self._maxValue:
			return self._maxValue
		return self._value

	def setRange(self, minValue, maxValue):
		if maxValue < minValue:
			maxValue = minValue
		self._minValue = minValue
		self._maxValue = maxValue

	def getMinValue(self):
		return self._minValue

	def getMaxValue(self):
		return self._maxValue

	def setHidden(self, value):
		self._hidden = value

	def getMinSize(self):
		return 250,12

	def _getPixelPos(self):
		x0, y0, w, h = self.getSize()
		#print self._parent._parent.GetSize()
		minSize = self.getMinSize()
		return x0 + w / 2, y0 + h / 2
		
		#x0, y0, w, h = self.getSize()
		##print self.getSize()
		#return x0 + w / 2, y0 + h / 2

	def getValueNormalized(self):
		if self._maxValue-self._minValue != 0:
			valueNormalized = ((self.getValue()-self._minValue)/(self._maxValue-self._minValue))
		else:
			valueNormalized = 0
		return valueNormalized
	def draw(self):
		if self._hidden:
			return

		w, h = self.getMinSize()
		# w -= 20
		pos = self._getPixelPos()

		glPushMatrix()
		glTranslatef(pos[0], pos[1], 0)
		glDisable(GL_TEXTURE_2D)
		# if self.hasFocus():
		# 	glColor4ub(60,60,60,130)
		# else:
		glColor3ub(128,128,128)
		glBegin(GL_QUADS)

		strokeWidth = 0
		barWidth = 1.5

		#Outside box
		glVertex2f( w/2+strokeWidth+barWidth,-h/2-strokeWidth)
		glVertex2f(-w/2-strokeWidth-barWidth,-h/2-strokeWidth)
		glVertex2f(-w/2-strokeWidth-barWidth, h/2+strokeWidth)
		glVertex2f( w/2+strokeWidth+barWidth, h/2+strokeWidth)
		glEnd()
		glColor3ub(188,188,188)
		glBegin(GL_QUADS)
		#Inside box
		glVertex2f( w/2+barWidth,-h/2)
		glVertex2f(-w/2-barWidth,-h/2)
		glVertex2f(-w/2-barWidth, h/2)
		glVertex2f( w/2+barWidth, h/2)
		glEnd()
		scrollLength = h - w
		valueNormalized = self.getValueNormalized()
		# if self._maxValue-self._minValue != 0:
		# 	valueNormalized = ((self.getValue()-self._minValue)/(self._maxValue-self._minValue))
		# else:
		# 	valueNormalized = 0
		# glTranslate(scrollLength/2,0.0,0)
		
		# if self._focus:
		#if 0:
			# glColor4ub(100,100,100,255)
			# glPushMatrix()
			# glTranslate(w,opengl.glGetStringSize(str(self._minValue))[1]/2,0)
			# opengl.glDrawStringLeft(str(self._minValue))
			# glTranslate(0,-scrollLength,0)
			# opengl.glDrawStringLeft(str(self._maxValue))
			# glColor4ub(0,0,0,255)
			# glTranslate(-w*3,scrollLength-scrollLength*valueNormalized-w/4,0)
			# opengl.glDrawStringRight(str(self.getValue()))
			# glPopMatrix()
		#
		# pauses = self._parent._pauses
		#
		# for pause in pauses:
		# 	glColor3ub(0,0,0)
		# 	glBegin(GL_QUADS)
		# 	glVertex2f(w*valueNormalized-w/2+barWidth,-h/2)
		# 	glVertex2f(-w/2-barWidth,-h/2)
		# 	glVertex2f(-w/2-barWidth, h/2)
		# 	glVertex2f(w*valueNormalized-w/2+barWidth, h/2)
		# 	glEnd()

		glColor3ub(140,198,63)
		# glTranslate(-scrollLength*valueNormalized,0.0,0)
		# glTranslate(-w/2,0.0,0)

		# the green slider bar
		glBegin(GL_QUADS)
		glVertex2f(w*valueNormalized-w/2+barWidth,-h/2)
		glVertex2f(-w/2-barWidth,-h/2)
		glVertex2f(-w/2-barWidth, h/2)
		glVertex2f(w*valueNormalized-w/2+barWidth, h/2)
		glEnd()

		# the green bar
		glTranslate(w*valueNormalized-w/2,0,0)
		glColor3ub(128,128,128)
		glBegin(GL_QUADS)
		glVertex2f( barWidth, h/2)
		glVertex2f(-barWidth, h/2)
		glVertex2f(-barWidth,-h/2)
		glVertex2f( barWidth,-h/2)
		glEnd()

		glBegin(GL_QUADS)
		glVertex2f(-barWidth, h/2)
		glVertex2f( barWidth, h/2)
		glVertex2f( barWidth,-h/1.5)
		glVertex2f(-barWidth,-h/1.5)
		glEnd()

		glBegin(GL_QUADS)
		glVertex2f( barWidth,-h/1.5)
		glVertex2f(-barWidth,-h/1.5)
		glVertex2f(-barWidth*4,-h/1.5-barWidth*5)
		glVertex2f( barWidth*4,-h/1.5-barWidth*5)
		glEnd()
		
		glPopMatrix()

	def _checkHit(self, x, y): #Modified this so the hitbox is a bit higher to accommodate the arrow
		if self._hidden or self._parent._progressBar:
			return False
		pos = self._getPixelPos()
		w, h = self.getMinSize()
		# return -w/2 <= x - pos[0] <= w/2 and -h/2 <= y - pos[1] <= h/2
		return -w/2-5 <= x - pos[0] <= w/2+5 and -h*3 <= y - pos[1] <= h/2

	def setFocus(self):
		self._base._focus = self
		return True

	def OnMouseMotion(self, x, y):
		if self.hasFocus():
			w, h = self.getMinSize()
			scrollLength = h - w
			pos = self._getPixelPos()
			self.setValue(int(self._minValue + (self._maxValue - self._minValue) * -(x - pos[0] - scrollLength/2) / scrollLength))
			self._callback()
			return True
		if self._checkHit(x, y):
			self._focus = True
			return True
		self._focus = False
		return False

	def OnMouseDown(self, x, y, button):
		if self._checkHit(x, y):
			self.setFocus()
			self.OnMouseMotion(x, y)
			return True
		return False

	def OnMouseUp(self, x, y):
		if self.hasFocus():
			self._base._focus = None
			return True
		return False

		
class glButtonSetting(glGuiControl):
	def __init__(self, parent, imageID, tooltip, pos, callback, Xnudge = 0, Ynudge = 0, size = None, scaleModifier = None, advanced = False):
		self._buttonSize = size
		self._scaleModifier = scaleModifier
		self._hidden = False
		super(glButtonSetting, self).__init__(parent,pos)
		self._tooltip = tooltip
		self._parent = parent
		self._imageID = imageID
		self._callback = callback
		self._selected = False
		self._focus = False
		self._disabled = False
		self._showExpandArrow = False
		self._progressBar = None
		self._altTooltip = ''
		self._Xnudge = Xnudge
		self._Ynudge = Ynudge
		self._default_Ynudge = Ynudge
		self._glDittoTexture = None
		self._advanced = advanced
		
		self._popup = Tooltip(parent)
		self._popup.Hide()
	def getImageID(self):
		return int(self._imageID)
		
	def setImageID(self, value):
		self._imageID = value
		
	def setSelected(self, value):
		self._selected = value

	def setExpandArrow(self, value):
		self._showExpandArrow = value

	def setHidden(self, value):
		self._hidden = value

	def setDisabled(self, value):
		self._disabled = value

	def setProgressBar(self, value):
		self._progressBar = value

	def getProgressBar(self):
		return self._progressBar

	def setBottomText(self, value):
		self._altTooltip = value

	def getSelected(self):
		return self._selected

	def getMinSize(self):
		if self._hidden:
			return 0, 0
		if self._buttonSize is not None:
			return self._buttonSize, self._buttonSize
		return self._base._buttonSize, self._base._buttonSize

	def _getPixelPos(self):
		windowWidth,windowHeight = self._parent.GetSize()
		x0, y0, w, h = self.getSize()
		x0 = self._Xnudge
		y0 = windowHeight - self._Ynudge
		return x0 + w / 2, y0 + h / 2

	def draw(self):
		if self._parent.settingsOpen == False:
			self._hidden = True
		else:
			self._hidden = False
		
		if self._hidden:
			return
		if self._advanced == True and self._parent.advancedOpen == False:
			return
		if self._advanced == False and self._parent.advancedOpen == False:
			self._Ynudge = self._default_Ynudge - self.YnudgeModifer
		elif self._advanced == None: #only for the advancedTabButton. No matter what it's position is -70.
			self._Ynudge = self._default_Ynudge - 70
		else:
			self._Ynudge = self._default_Ynudge
			
		cx = (self._imageID % 4) / 4
		cy = int(self._imageID / 4) / 4
		bs = self.getMinSize()[0]
		pos = self._getPixelPos()
        
        

		if self._imageID < 32:
			glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture)
		else:
			glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture2)
			

		if self._disabled:
			glColor4ub(128,128,128,128)
		else:
			glColor4ub(255,255,255,156)
			
		scale = 1



		if self._selected:
			scale = 1
			glColor3ub(*self.settingsSelectedColour)
		elif self._focus:
			#scale = 0.9
			if self._imageID != 21:#not the upper left logo
				#glColor4ub(43,222,115,255)
				glColor4ub(255,255,255,255)
			glColor3ub(*self.buttonSelectedColour)
		else:
			glColor3ub(*self.settingsUnselectedColour)
		#opengl.glDrawTexturedQuad(self._Xnudge+pos[0]-bs*scale/2, self._Ynudge + pos[1]-bs*scale/2, bs*scale, bs*scale, 0)
		opengl.glDrawTexturedQuad(pos[0]-bs*scale/2, pos[1]-bs*scale/2, bs*scale, bs*scale, self._imageID)
		#print pos[1]-bs*scale/2
		#if self._showExpandArrow:
		#	if self._selected:
		#		opengl.glDrawTexturedQuad(pos[0]+bs*scale/2-bs*scale/4*1.2, pos[1]-bs*scale/2*1.2, bs*scale/4, bs*scale/4, 1)
		#	else:
		#		opengl.glDrawTexturedQuad(pos[0]+bs*scale/2-bs*scale/4*1.2, pos[1]-bs*scale/2*1.2, bs*scale/4, bs*scale/4, 1, 2)
		glPushMatrix()
		glTranslatef(pos[0], pos[1], 0)
		glDisable(GL_TEXTURE_2D)
		if self._focus and 0:
			glTranslatef(0, -0.55*bs*scale, 0)

			glPushMatrix()
			glColor4ub(60,60,60,255)
			glTranslatef(-1, -1, 0)
			opengl.glDrawStringCenter(self._tooltip)
			glTranslatef(0, 2, 0)
			opengl.glDrawStringCenter(self._tooltip)
			glTranslatef(2, 0, 0)
			opengl.glDrawStringCenter(self._tooltip)
			glTranslatef(0, -2, 0)
			opengl.glDrawStringCenter(self._tooltip)
			glPopMatrix()

			glColor4ub(255,255,255,255)
			opengl.glDrawStringCenter(self._tooltip)
			glPopMatrix()
			if 0:
				if self._glDittoTexture is None:
					self._glDittoTexture = opengl.loadGLTexture('import_text2.png')

				glBindTexture(GL_TEXTURE_2D, self._glDittoTexture)
				glEnable(GL_TEXTURE_2D)
				glPushMatrix()
				glColor4f(1,1,1,1)
				glTranslate(180, 160,100)
				glScale(160,49,100)
				glBegin(GL_QUADS)
				glTexCoord2f(1, 0)
				glVertex2f(0,-1)
				glTexCoord2f(0, 0)
				glVertex2f(-1,-1)
				glTexCoord2f(0, 1)
				glVertex2f(-1, 0)
				glTexCoord2f(1, 1)
				glVertex2f(0, 0)
			glEnd()
			glDisable(GL_TEXTURE_2D)
			
		glPopMatrix()



	def _checkHit(self, x, y):
		if self._hidden or self._disabled or self._parent._progressBar:
			return False
		bs = self.getMinSize()[0] * self._scaleModifier
		pos = self._getPixelPos()
		return -bs * 0.5 <= x - pos[0] <= bs * 0.5 and -bs * 0.5 <= y - pos[1] <= bs * 0.5
		

	def OnMouseMotion(self, x, y):
		
		#if self._tooltip != '':
		#	return
		if self._checkHit(x, y):
			self._focus = True
			if not self._popup.showing and self._tooltip != '':
				pos = self._getPixelPos()
				self._popup.OnPopupDisplay(self._tooltip, pos[0],pos[1])
			return True
			
		if self._popup.showing:
			self._popup.OnPopupHide(self)
		self._focus = False
		return False

	def OnMouseDown(self, x, y, button):
		#if self._tooltip == '':
		#	return
		if self._checkHit(x, y):
			self._callback(button)
			#self.setSelected(True)
			return True
		return False
		
class glRadioButtonSetting(glButtonSetting):
	def __init__(self, parent, imageID, tooltip, pos, group, callback, Xnudge = 0, Ynudge = 0, size = None, scaleModifier = None, advanced = False):
		super(glRadioButtonSetting, self).__init__(parent, imageID, tooltip, pos, self._onRadioSelect, Xnudge, Ynudge, size, scaleModifier, advanced) #this is the init for glButtonSetting
		
		#self, parent, imageID, tooltip, pos, callback, Xnudge = 0, Ynudge = 0, size = None
		
		self._group = group
		self._radioCallback = callback
		self._group.append(self)
		
	def setSelected(self, value):
		self._selected = value

	def _onRadioSelect(self, button):
		self._base._focus = None
		for ctrl in self._group:
			if ctrl != self:
				ctrl.setSelected(False)
		if self.getSelected():
			pass
			#self.setSelected(False)
		else:
			self.setSelected(True)
		self._radioCallback(button)

class glCameraRadioButtonSetting(glRadioButton):
	def __init__(self, parent, imageID, pos, group, callback, Xnudge = 0, Ynudge = 0, size = None, type = None):
		super(glCameraRadioButtonSetting, self).__init__(parent, imageID, '', '', pos, group, self._onRadioSelect,0,0,1,None,"none")
		self._buttonSize = size
		self._type = type
		self._group = group
		self._radioCallback = callback
		self._group.append(self)
		
		self._Xnudge = Xnudge
		self._Ynudge = Ynudge
		

	def setSelected(self, value):
		self._selected = value

	def _onRadioSelect(self, button):
		self._base._focus = None
		for ctrl in self._group:
			if ctrl != self:
				ctrl.setSelected(False)
		if self.getSelected():
			pass
			#self.setSelected(False)
		else:
			self.setSelected(True)
		self._radioCallback(button)
		
	def getMinSize(self):
		if self._hidden:
			return 0, 0
		if self._buttonSize is not None:
			return self._buttonSize, self._buttonSize
			
		return self._base._buttonSize, self._base._buttonSize
		
	def _getPixelPos(self):
		windowWidth,windowHeight = self._parent.GetSize()
		x0, y0, w, h = self.getSize()
		#print self.getSize()
		#print x0 + w / 2, y0 + h / 2
		return self._Xnudge + windowWidth / 2, windowHeight - self._Ynudge - y0 + h / 2

	def draw(self):
		if self._type == 'camera':
			if self._parent.cameraOpen == False:
				self._hidden = True
			else:
				self._hidden = False
		if self._type == 'viewmode':
			if self._parent.viewmodeOpen == False:
				self._hidden = True
			else:
				self._hidden = False
		



		if self._hidden:
			return

		cx = (self._imageID % 4) / 4
		cy = int(self._imageID / 4) / 4
		bs = self._buttonSize
		pos = self._getPixelPos()

		if self._imageID < 32:
			glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture)
		else:
			glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture2)
		if self._disabled:
			glColor4ub(128,128,128,128)
		else:
			glColor4ub(255,255,255,255)
			
		scale = 1
		if self._selected:
			glColor3ub(*self.altButtonHighlightColour)
		elif self._focus:
			glColor3ub(*self.altButtonHighlightColour)
		else:
			glColor4ub(*self.buttonUnselectedColour)
		#opengl.glDrawTexturedQuad(self._Xnudge+pos[0]-bs*scale/2, self._Ynudge + pos[1]-bs*scale/2, bs*scale, bs*scale, 0)
		opengl.glDrawTexturedQuad(pos[0]-bs*scale/2, pos[1]-bs*scale/2, bs*scale, bs*scale, self._imageID)
		if self._showExpandArrow:
			if self._selected:
				opengl.glDrawTexturedQuad(pos[0]+bs*scale/2-bs*scale/4*1.2, pos[1]-bs*scale/2*1.2, bs*scale/4, bs*scale/4, 1)
			else:
				opengl.glDrawTexturedQuad(pos[0]+bs*scale/2-bs*scale/4*1.2, pos[1]-bs*scale/2*1.2, bs*scale/4, bs*scale/4, 1, 2)
		glPushMatrix()
		glTranslatef(pos[0], pos[1], 0)
		glDisable(GL_TEXTURE_2D)
		if self._focus:
			
			glTranslatef(0, -0.55*bs*scale, 0)
			glPopMatrix()
			
			
		glPopMatrix()
		progress = self._progressBar
		if progress is not None:
			glColor4ub(60,60,60,255)
			opengl.glDrawQuad(pos[0]-bs/2, pos[1]+bs/2, bs, bs / 4)
			glColor4ub(255,255,255,255)
			opengl.glDrawQuad(pos[0]-bs/2+2, pos[1]+bs/2+2, (bs - 5) * progress + 1, bs / 4 - 4)

	def _checkHit(self, x, y): #TODO
		if self._hidden or self._disabled:
			return False
		bs = self.getMinSize()[0]
		pos = self._getPixelPos()
		#print self._extraHitbox
		if self._extraHitbox:
			#print "new"
			return self._extraHitbox[0] <= x - pos[0] <= self._extraHitbox[1] and self._extraHitbox[2] <= y - pos[1] <= self._extraHitbox[3]


		#print -bs * 0.5 <= x - pos[0] <= bs * 0.5 and -bs * 0.5 <= y - pos[1] <= bs * 0.5
		return -bs * 0.5 <= x - pos[0] <= bs * 0.5 and -bs * 0.5 <= y - pos[1] <= bs * 0.5
		
	def OnMouseMotion(self, x, y):
		if self._checkHit(x, y):
			self._focus = True
			return True
			
		self._focus = False
		return False

	def OnMouseDown(self, x, y, button):
		if self._checkHit(x, y):
			self._callback(button)
			return True
		return False
		
class glViewmodeRadioButtonSetting(glRadioButtonSetting):
	def __init__(self, parent, imageID, tooltip, pos, group, callback, Xnudge = 0, Ynudge = 0, size = None, advanced = False):
		super(glViewmodeRadioButtonSetting, self).__init__(parent, imageID, tooltip, pos, group, self._onRadioSelect, Xnudge, Ynudge, size, advanced) #this is the init for glButtonSetting
		
		#self, parent, imageID, tooltip, pos, callback, Xnudge = 0, Ynudge = 0, size = None
		
		self._group = group
		self._radioCallback = callback
		self._group.append(self)

	def setSelected(self, value):
		self._selected = value

	def _onRadioSelect(self, button):
		self._base._focus = None
		for ctrl in self._group:
			if ctrl != self:
				ctrl.setSelected(False)
		if self.getSelected():
			self.setSelected(False)
		else:
			self.setSelected(True)
		self._radioCallback(button)
		
	def draw(self):
		if self._parent.viewmodeOpen == False:
			self._hidden = True
		else:
			self._hidden = False
		
		if self._hidden:
			return
		
		cx = (self._imageID % 4) / 4
		cy = int(self._imageID / 4) / 4
		bs = self.getMinSize()[0] #i don't use this anymore
		pos = self._getPixelPos()
		glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture)
			

		if self._disabled:
			glColor4ub(128,128,128,128)
		else:
			glColor4ub(255,255,255,156)
			
		scale = 1
		if self._selected:
			scale = 1.05
			glColor4ub(255,0,0,255)
		elif self._focus:
			#scale = 0.9
			if self._imageID != 21:#not the upper left logo
				#glColor4ub(43,222,115,255)
				glColor4ub(255,255,255,255)
			glColor4ub(200,200,200,255)
		else:
			glColor4ub(200,200,200,255)
		#opengl.glDrawTexturedQuad(self._Xnudge+pos[0]-bs*scale/2, self._Ynudge + pos[1]-bs*scale/2, bs*scale, bs*scale, 0)
		opengl.glDrawTexturedQuad(pos[0]-bs*scale/2, pos[1]-bs*scale/2, bs*scale, bs*scale, self._imageID)
		#print pos[1]-bs*scale/2
		#if self._showExpandArrow:
		#	if self._selected:
		#		opengl.glDrawTexturedQuad(pos[0]+bs*scale/2-bs*scale/4*1.2, pos[1]-bs*scale/2*1.2, bs*scale/4, bs*scale/4, 1)
		#	else:
		#		opengl.glDrawTexturedQuad(pos[0]+bs*scale/2-bs*scale/4*1.2, pos[1]-bs*scale/2*1.2, bs*scale/4, bs*scale/4, 1, 2)
		glPushMatrix()
		glTranslatef(pos[0], pos[1], 0)
		glDisable(GL_TEXTURE_2D)
		if self._focus:
			glTranslatef(0, -0.55*bs*scale, 0)

			glPushMatrix()
			glColor4ub(60,60,60,255)
			glTranslatef(-1, -1, 0)
			opengl.glDrawStringCenter(self._tooltip)
			glTranslatef(0, 2, 0)
			opengl.glDrawStringCenter(self._tooltip)
			glTranslatef(2, 0, 0)
			opengl.glDrawStringCenter(self._tooltip)
			glTranslatef(0, -2, 0)
			opengl.glDrawStringCenter(self._tooltip)
			glPopMatrix()

			glColor4ub(255,255,255,255)
			opengl.glDrawStringCenter(self._tooltip)
			glPopMatrix()
			if 0:
				if self._glDittoTexture is None:
					self._glDittoTexture = opengl.loadGLTexture('import_text2.png')

				glBindTexture(GL_TEXTURE_2D, self._glDittoTexture)
				glEnable(GL_TEXTURE_2D)
				glPushMatrix()
				glColor4f(1,1,1,1)
				glTranslate(180, 160,100)
				glScale(160,49,100)
				glBegin(GL_QUADS)
				glTexCoord2f(1, 0)
				glVertex2f(0,-1)
				glTexCoord2f(0, 0)
				glVertex2f(-1,-1)
				glTexCoord2f(0, 1)
				glVertex2f(-1, 0)
				glTexCoord2f(1, 1)
				glVertex2f(0, 0)
			glEnd()
			glDisable(GL_TEXTURE_2D)
			
		glPopMatrix()

class glTextLabelSetting(glGuiControl):
	def __init__(self, parent, tooltip, pos, Xnudge = 0, Ynudge = 0, fontSize = 12, advanced = False, colour = None):
		self._fontSize = fontSize
		#self._buttonSize = size
		self._hidden = False
		self._advanced = advanced
		super(glTextLabelSetting, self).__init__(parent,pos)
		self._tooltip = tooltip
		self._parent = parent
		#self._callback = callback
		self._selected = False
		self._focus = False
		self._disabled = False
		self._showExpandArrow = False
		self._progressBar = None
		self._altTooltip = ''
		self._Xnudge = Xnudge
		self._Ynudge = Ynudge
		self._default_Ynudge = Ynudge
		self._glDittoTexture = None
		if colour != None:
			self._colour = colour
		else:
			self._colour = self.settingsTextColour
		self.loaded = False
		
		self._oldText = None
		self._currentTexture = None
		
		self._counter = 0
		
		self._tooltipText = tooltipText.tooltipText(200, 200, self._tooltip, "roboto-light.ttf", self._fontSize, self._colour) #(43,182,115)
		#self._tooltipText.makeText()
		
		self._timer = -1
		
	def setTooltip(self, value):
		self._tooltip = value
	
	def getTooltip(self):
		return self._tooltip
		
	def setSelected(self, value):
		self._selected = value

	def setExpandArrow(self, value):
		self._showExpandArrow = value

	def setHidden(self, value):
		self._hidden = value

	def setDisabled(self, value):
		self._disabled = value

	def setProgressBar(self, value):
		self._progressBar = value

	def getProgressBar(self):
		return self._progressBar

	def setBottomText(self, value):
		self._altTooltip = value

	def getSelected(self):
		return self._selected

	def getMinSize(self):
		if self._hidden:
			return 0, 0
		#if self._buttonSize is not None:
		#	return self._buttonSize, self._buttonSize
		return self._base._buttonSize, self._base._buttonSize

	def _getPixelPos(self):
		windowWidth,windowHeight = self._parent.GetSize()
		x0, y0, w, h = self.getSize()
		x0 = self._Xnudge
		y0 = windowHeight - self._Ynudge
		return x0 + w / 2, y0 + h / 2

	def setTooltipText(self, text):
		self._tooltipText._text = text

	def draw(self):
		if self._parent.settingsOpen == False:
			self._hidden = True
		else:
			self._hidden = False
		if self._hidden:
			return
			
		if self._timer > 0:
			self._timer -=1
		if self._timer == 0:
			return
			
		#print self._parent.advancedOpen
		#print self._advanced5
		if self._advanced == True and self._parent.advancedOpen == False:
			return
		if self._advanced == False and self._parent.advancedOpen == False:
			self._Ynudge = self._default_Ynudge - self.YnudgeModifer
		else:
			self._Ynudge = self._default_Ynudge
		#cx = (self._imageID % 4) / 4
		#cy = int(self._imageID / 4) / 4
		bs = self.getMinSize()[0] #i don't use this anymore
		pos = self._getPixelPos()
		#glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture)
			

		if self._disabled:
			glColor4ub(128,128,128,128)
		else:
			glColor4ub(255,255,255,255)
			
		#scale = 0.8
		#if self._selected:
		#	scale = 0.85
		#	glColor4ub(255,25,0,255)
		#elif self._focus:
			#scale = 0.9
		#	if self._imageID != 21: #not the upper left logo 
		#		glColor4ub(43,222,115,255)

		#opengl.glDrawTexturedQuad(self._Xnudge+pos[0]-bs*scale/2, self._Ynudge + pos[1]-bs*scale/2, bs*scale, bs*scale, 0)
		#opengl.glDrawTexturedQuad(pos[0]-64*scale/2, pos[1]-64*scale/2, 64*scale, 64*scale, self._imageID)
		#print pos[1]-bs*scale/2
		glEnd()
		glPushMatrix()
		#glTranslatef(pos[0], pos[1], 0)
		glDisable(GL_TEXTURE_2D)
		#glColor4ub(255,255,255,255)
		#if self.loaded == False:
		#	self.abc = testtext.font_data("font.ttf",self._fontSize)
		#	self.loaded = True
		
		windowWidth,windowHeight = self._parent.GetSize()
		#self.abc.glPrint(500,500,str(self.bla))
		#self.abc.glPrint(pos[0],windowHeight-pos[1],self._tooltip)

		self._tooltipText._x = pos[0]
		self._tooltipText._y = pos[1]
		self._tooltipText._text = self._tooltip
		
		if self._oldText != self._tooltipText._text:
			#glBindTexture(GL_TEXTURE_2D, opengl.loadGLTexture2(self._tooltipText.makeText()))
			self._currentTexture = self._tooltipText.makeText()
			self._oldText = self._tooltipText._text
			self._counter+= 1
			print self._counter
			
		glBindTexture(GL_TEXTURE_2D, opengl.loadGLTexture2(self._currentTexture, self._tooltipText._textWidth, self._tooltipText._textHeight))

		self._tooltipText.displayText()
		
		
		#if self._focus:
		if 0:
			glTranslatef(0, -0.55*bs*scale, 0)

			glPushMatrix()
			glColor4ub(60,60,60,255)
			glTranslatef(-1, -1, 0)
			opengl.glDrawStringCenter(self._tooltip)
			glTranslatef(0, 2, 0)
			opengl.glDrawStringCenter(self._tooltip)
			glTranslatef(2, 0, 0)
			opengl.glDrawStringCenter(self._tooltip)
			glTranslatef(0, -2, 0)
			opengl.glDrawStringCenter(self._tooltip)
			glPopMatrix()

			glColor4ub(255,255,255,255)
			opengl.glDrawStringCenter(self._tooltip)
			glPopMatrix()
			if self._glDittoTexture is None:
				self._glDittoTexture = opengl.loadGLTexture('import_text2.png')

			glBindTexture(GL_TEXTURE_2D, self._glDittoTexture)
			glEnable(GL_TEXTURE_2D)
			glPushMatrix()
			glColor4f(1,1,1,1)
			glTranslate(180, 160,100)
			glScale(160,49,100)
			glBegin(GL_QUADS)
			glTexCoord2f(1, 0)
			glVertex2f(0,-1)
			glTexCoord2f(0, 0)
			glVertex2f(-1,-1)
			glTexCoord2f(0, 1)
			glVertex2f(-1, 0)
			glTexCoord2f(1, 1)
			glVertex2f(0, 0)
			glEnd()
			glDisable(GL_TEXTURE_2D)
			
		glPopMatrix()
		progress = self._progressBar
		if progress is not None:
			glColor4ub(60,60,60,255)
			opengl.glDrawQuad(pos[0]-bs/2, pos[1]+bs/2, bs, bs / 4)
			glColor4ub(255,255,255,255)
			opengl.glDrawQuad(pos[0]-bs/2+2, pos[1]+bs/2+2, (bs - 5) * progress + 1, bs / 4 - 4)
		elif len(self._altTooltip) > 0:
			glPushMatrix()
			glTranslatef(pos[0], pos[1], 0)
			glTranslatef(0.6*bs*scale, 0, 0)

			glPushMatrix()
			glColor4ub(60,60,60,255)
			glTranslatef(-1, -1, 0)
			opengl.glDrawStringLeft(self._altTooltip)
			glTranslatef(0, 2, 0)
			opengl.glDrawStringLeft(self._altTooltip)
			glTranslatef(2, 0, 0)
			opengl.glDrawStringLeft(self._altTooltip)
			glTranslatef(0, -2, 0)
			opengl.glDrawStringLeft(self._altTooltip)
			glPopMatrix()

			glColor4ub(255,255,0,255)
			opengl.glDrawStringLeft(self._altTooltip)
			glPopMatrix()

	def _checkHit(self, x, y):
		if self._hidden or self._disabled or self._parent._progressBar:
			return False
		bs = self.getMinSize()[0]
		pos = self._getPixelPos()
		length = len(self._tooltip) * 7
		#print pos
		return 0 <= x - pos[0] <= length and -bs * 0.5 <= y - pos[1] <= bs * 0.5

	def OnMouseMotion(self, x, y):
		if self._tooltip == '':
			return
		
		if self._checkHit(x, y):
			self._focus = True
			#self._tooltip = "X:" + str(x)
			return True
		self._focus = False
		return False

	def OnMouseDown(self, x, y, button):
		if self._tooltip == '':
			return
		if self._checkHit(x, y):
			#self._callback(button)
			#self.setSelected(True)
			return True
		return False

class glModal(glGuiControl):
	def __init__(self, parent, pos, center = "none"):
		self._parent = parent
		super(glModal, self).__init__(parent, pos)
		self._elements = []
		self._center = center
		self._hidden = False
		for e in self._elements:
			e._hidden = False

	def _getPixelPos(self):
		x0, y0, w, h = self.getSize()
		#print self.getSize()
		return x0 + w / 2,y0 + h / 2

	def draw(self):
		if self._hidden:
			return
		sceneSize = self._parent.GetSize()
		glPopMatrix()
		x0, y0, w, h = self.getSize()
		glColor4ub(50,50,50,130)

		opengl.glDrawQuad(0, 0, sceneSize[0], sceneSize[1])
		glPopMatrix()

	def showModal(self, e = None):
		self._hidden = False
		for e in self._elements:
			e._hidden = False

	def setElements(self, elements):
		self._elements = elements

	def closeModal(self, e = None):
		self._hidden = True
		for e in self._elements:
			e._hidden = True

	# def _checkHit(self, x, y):
	# 	return True
	# 	if self._hidden:
	# 		return False
	# 	pos = self._getPixelPos()
	#
	# 	return -bs * 0.5 <= x - pos[0] <= bs * 0.5 and -bs * 0.5 <= y - pos[1] <= bs * 0.5

	def OnMouseMotion(self, x, y):
		return
		# if self._checkHit(x, y):
		# 	self._focus = True
		# 	return True
		# self._focus = False
		# return False

	def OnMouseDown(self, x, y, button):
		if self._hidden:
			return False
		self.closeModal()
		return True
		# if self._checkHit(x, y):
			# self._callback(button)
			# return True
		# return False








































