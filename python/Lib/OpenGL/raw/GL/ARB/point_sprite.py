'''OpenGL extension ARB.point_sprite

Automatically generated by the get_gl_extensions script, do not edit!
'''
from OpenGL import platform, constants, constant, arrays
from OpenGL import extensions
from OpenGL.GL import glget
import ctypes
EXTENSION_NAME = 'GL_ARB_point_sprite'
_DEPRECATED = False
GL_POINT_SPRITE_ARB = constant.Constant( 'GL_POINT_SPRITE_ARB', 0x8861 )
glget.addGLGetConstant( GL_POINT_SPRITE_ARB, (1,) )
GL_COORD_REPLACE_ARB = constant.Constant( 'GL_COORD_REPLACE_ARB', 0x8862 )


def glInitPointSpriteARB():
    '''Return boolean indicating whether this extension is available'''
    return extensions.hasGLExtension( EXTENSION_NAME )
