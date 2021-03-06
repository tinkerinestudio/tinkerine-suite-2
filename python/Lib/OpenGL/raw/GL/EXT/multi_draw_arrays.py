'''OpenGL extension EXT.multi_draw_arrays

Automatically generated by the get_gl_extensions script, do not edit!
'''
from OpenGL import platform, constants, constant, arrays
from OpenGL import extensions
from OpenGL.GL import glget
import ctypes
EXTENSION_NAME = 'GL_EXT_multi_draw_arrays'
_DEPRECATED = False

glMultiDrawArraysEXT = platform.createExtensionFunction( 
'glMultiDrawArraysEXT',dll=platform.GL,
extension=EXTENSION_NAME,
resultType=None, 
argTypes=(constants.GLenum,arrays.GLintArray,arrays.GLsizeiArray,constants.GLsizei,),
doc='glMultiDrawArraysEXT(GLenum(mode), GLintArray(first), GLsizeiArray(count), GLsizei(primcount)) -> None',
argNames=('mode','first','count','primcount',),
deprecated=_DEPRECATED,
)

glMultiDrawElementsEXT = platform.createExtensionFunction( 
'glMultiDrawElementsEXT',dll=platform.GL,
extension=EXTENSION_NAME,
resultType=None, 
argTypes=(constants.GLenum,arrays.GLsizeiArray,constants.GLenum,ctypes.POINTER(ctypes.c_void_p),constants.GLsizei,),
doc='glMultiDrawElementsEXT(GLenum(mode), GLsizeiArray(count), GLenum(type), POINTER(ctypes.c_void_p)(indices), GLsizei(primcount)) -> None',
argNames=('mode','count','type','indices','primcount',),
deprecated=_DEPRECATED,
)


def glInitMultiDrawArraysEXT():
    '''Return boolean indicating whether this extension is available'''
    return extensions.hasGLExtension( EXTENSION_NAME )
