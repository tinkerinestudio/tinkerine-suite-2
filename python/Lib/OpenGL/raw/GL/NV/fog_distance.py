'''OpenGL extension NV.fog_distance

Automatically generated by the get_gl_extensions script, do not edit!
'''
from OpenGL import platform, constants, constant, arrays
from OpenGL import extensions
from OpenGL.GL import glget
import ctypes
EXTENSION_NAME = 'GL_NV_fog_distance'
_DEPRECATED = False
GL_FOG_DISTANCE_MODE_NV = constant.Constant( 'GL_FOG_DISTANCE_MODE_NV', 0x855A )
glget.addGLGetConstant( GL_FOG_DISTANCE_MODE_NV, (1,) )
GL_EYE_RADIAL_NV = constant.Constant( 'GL_EYE_RADIAL_NV', 0x855B )
GL_EYE_PLANE_ABSOLUTE_NV = constant.Constant( 'GL_EYE_PLANE_ABSOLUTE_NV', 0x855C )


def glInitFogDistanceNV():
    '''Return boolean indicating whether this extension is available'''
    return extensions.hasGLExtension( EXTENSION_NAME )
