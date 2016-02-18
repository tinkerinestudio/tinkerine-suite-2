import PIL
from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw
from Cura.gui.util import opengl
from OpenGL.GL import *
class tooltipText(object):
	def __init__(self, x, y, text, font, fontsize, colour, alignment = "center", backgroundColour = None):
		self._x = 0
		self._y = 0
		self._xNudge = x
		self._yNudge = y
		self._text = text
		self._font = font
		self._fontsize = fontsize
		self._colour = colour
		self._pBits = None
		self._oldtext = ""
		self._texture = None
		self._textList = []
		self.mode = None
		self.alignment = alignment

		self._backgroundColour = backgroundColour

		self._textWidth = 64
		self._textHeight = 64

		self._textSize = (0,0)
		self.makeText()

		#self.displayText()
	def makeText(self, forceRemake = False):
		if self._oldtext != self._text or forceRemake == True:
			font = ImageFont.truetype(self._font,self._fontsize)

			# self._textSize = font.getsize(self._text)

			self._textList = self._text.split('\n')

			powers = [2,4,8,16,32,64,128,256,512,1024,2048,4096,8192,16384]
			self._textSize = (0,0)
			for t in self._textList:
				tSize = font.getsize(t)
				if tSize[0] >= self._textSize[0]:
					self._textSize = tSize
			# print self._text, self._textSize
			# self._textSize = font.getsize(self._text)
			# print self._text, self._textSize

			self._textWidth = 25 + int(len(self._text) * float(self._fontsize)/1.8)
			self._textHeight = (self._fontsize+3)*len(self._textList)

			for i in range(0, len(powers)):
				if self._textWidth <= powers[i]:
					self._textWidth = powers[i]
					break

			for i in range(0, len(powers)):
				if self._textHeight <= powers[i]:
					self._textHeight = powers[i]
					break

			img=Image.new("RGBA", (self._textWidth,self._textHeight*5),(self._colour[0],self._colour[1],self._colour[2],0))

			draw = ImageDraw.Draw(img)
			for x in range(1, len(self._textList)+1):
				draw.text((0, (self._textHeight-self._fontsize-5)-((x-1)*(self._fontsize+2))),self._textList[-x],self._colour,font=font)
			draw = ImageDraw.Draw(img)

			#draw = ImageDraw.Draw(img)
			# img_flip = img.transpose(Image.FLIP_TOP_BOTTOM)
			#draw = ImageDraw.Draw(img)
			#draw = ImageDraw.Draw(img)

			pBits2 = img.tostring("raw", "RGBA")
			# pBits = img_flip.tostring("raw", "RGBA")
			#print "i made a pbit"
			self._pBits = pBits2
			#self.displayText()
			self._oldtext = self._text
			#print "making text!"
			return self._pBits
		else:
			#print "found premade text!"
			return self._pBits


	def displayText2(self):
		numLines = len(self._textList)

		if self._backgroundColour != None:
			glPopMatrix()
			glColor4ub(128,128,128,128)
			opengl.glDrawQuad(self._x+self._xNudge-6,self._y+1+self._yNudge,self._textSize[0]+11,(-(self._fontsize+2)*len(self._textList))-7)
			glColor4ub(252,244,185,255)
			opengl.glDrawQuad(self._x+self._xNudge-5,self._y+self._yNudge,self._textSize[0]+9,(-(self._fontsize+2)*len(self._textList))-5)
			glPopMatrix()

		glEnable(GL_TEXTURE_2D)
		glPushMatrix()
		glColor4f(1,1,1,1)
		if self.alignment == "left":
			glTranslate(self._x+self._xNudge+self._textWidth+self._textSize[0]/2, self._y+self._yNudge,0)
		elif self.alignment == "right":
			glTranslate(self._x+self._xNudge+self._textWidth+self._textSize[0], self._y+self._yNudge,0)
		else:
			glTranslate(self._x+self._xNudge+self._textWidth, self._y+self._yNudge,0)

		glScale( self._textWidth,self._textHeight,0)
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
	def displayText(self):
		glEnable(GL_TEXTURE_2D)
		glPushMatrix()
		glColor4f(1,1,1,1)
		glTranslate(self._x+self._textWidth, self._y,0)
		glScale( self._textWidth,self._textHeight,0)
			
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