'''OpenGL extension SGIX.igloo_interface

Automatically generated by the get_gl_extensions script, do not edit!
'''
from OpenGL import platform, constants, constant, arrays
from OpenGL import extensions
from OpenGL.GL import glget
import ctypes
EXTENSION_NAME = 'GL_SGIX_igloo_interface'
_DEPRECATED = False

glIglooInterfaceSGIX = platform.createExtensionFunction( 
'glIglooInterfaceSGIX',dll=platform.GL,
extension=EXTENSION_NAME,
resultType=None, 
argTypes=(constants.GLenum,ctypes.c_void_p,),
doc='glIglooInterfaceSGIX(GLenum(pname), c_void_p(params)) -> None',
argNames=('pname','params',),
deprecated=_DEPRECATED,
)


def glInitIglooInterfaceSGIX():
    '''Return boolean indicating whether this extension is available'''
    return extensions.hasGLExtension( EXTENSION_NAME )
