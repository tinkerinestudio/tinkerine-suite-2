'''OpenGL extension EXT.gpu_program_parameters

Automatically generated by the get_gl_extensions script, do not edit!
'''
from OpenGL import platform, constants, constant, arrays
from OpenGL import extensions
from OpenGL.GL import glget
import ctypes
EXTENSION_NAME = 'GL_EXT_gpu_program_parameters'
_DEPRECATED = False

glProgramEnvParameters4fvEXT = platform.createExtensionFunction( 
'glProgramEnvParameters4fvEXT',dll=platform.GL,
extension=EXTENSION_NAME,
resultType=None, 
argTypes=(constants.GLenum,constants.GLuint,constants.GLsizei,arrays.GLfloatArray,),
doc='glProgramEnvParameters4fvEXT(GLenum(target), GLuint(index), GLsizei(count), GLfloatArray(params)) -> None',
argNames=('target','index','count','params',),
deprecated=_DEPRECATED,
)

glProgramLocalParameters4fvEXT = platform.createExtensionFunction( 
'glProgramLocalParameters4fvEXT',dll=platform.GL,
extension=EXTENSION_NAME,
resultType=None, 
argTypes=(constants.GLenum,constants.GLuint,constants.GLsizei,arrays.GLfloatArray,),
doc='glProgramLocalParameters4fvEXT(GLenum(target), GLuint(index), GLsizei(count), GLfloatArray(params)) -> None',
argNames=('target','index','count','params',),
deprecated=_DEPRECATED,
)


def glInitGpuProgramParametersEXT():
    '''Return boolean indicating whether this extension is available'''
    return extensions.hasGLExtension( EXTENSION_NAME )
