'''OpenGL extension VERSION.GL_2_1_DEPRECATED

This module customises the behaviour of the 
OpenGL.raw.GL.VERSION.GL_2_1_DEPRECATED to provide a more 
Python-friendly API

The official definition of this extension is available here:
http://www.opengl.org/registry/specs/VERSION/GL_2_1_DEPRECATED.txt
'''
from OpenGL import platform, constants, constant, arrays
from OpenGL import extensions, wrapper
from OpenGL.GL import glget
import ctypes
from OpenGL.raw.GL.VERSION.GL_2_1_DEPRECATED import *
### END AUTOGENERATED SECTION