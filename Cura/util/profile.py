from __future__ import absolute_import
from __future__ import division

import os, traceback, math, re, zlib, base64, time, sys, platform, glob, string, stat
import cPickle as pickle
if sys.version_info[0] < 3:
	import ConfigParser
else:
	import configparser as ConfigParser

from Cura.util import resources
from Cura.util import version

#########################################################
## Default settings when none are found.
#########################################################

#Single place to store the defaults, so we have a consistent set of default settings.
####Old alterationDefault####
# alterationDefault = {
profileDefaultSettings = {
	'nozzle_size': '0.4',
	'layer_height': '0.2',
	'wall_thickness': '2',
	'solid_layer_thickness': '0.2',
	'fill_density': '18',
	'skirt_line_count': '2',
	'skirt_gap': '2.0',
	'print_speed': '70',
	'print_flow': '1',
	'print_temperature': '220',
	'first_layer_print_temperature': '220',
	'print_bed_temperature': '70',
	'filament_diameter': '1.75',
	'filament_density': '1.00',
	'retraction_min_travel': '3',
	'retraction_enable': 'true',
	'retraction_speed': '80.0',
	'retraction_amount': '0.8',
	'retraction_extra': '0.0',
	'retract_on_jumps_only': 'False',
	'travel_speed': '200',
	'max_z_speed': '3.0',
	'bottom_layer_speed': '30',
	'cool_min_layer_time': '5',
	'fan_enabled': 'True',
	'fan_layer': '1',
	'fan_speed': '100',
	'fan_speed_max': '100',
	'model_scale': '1.0',
	'flip_x': 'False',
	'flip_y': 'False',
	'flip_z': 'False',
	'swap_xz': 'False',
	'swap_yz': 'False',
	'model_rotate_base': '0',
	'model_multiply_x': '1',
	'model_multiply_y': '1',
	'extra_base_wall_thickness': '0.0',
	'sequence': 'Loops > Perimeter > Infill',
	'force_first_layer_sequence': 'True',
	'infill_type': 'Grid Rectangular',
	'solid_top': 'True',
	'fill_overlap': '0',
	'support_rate': '50',
	'support_distance': '0.5',
	'support_dual_extrusion': 'False',
	'joris': 'False',
	'enable_skin': 'False',
	'enable_raft': 'False',
	'cool_min_feedrate': '5',
	'bridge_speed': '90',
	'raft_margin': '3',
	'raft_base_material_amount': '100',
	'raft_interface_material_amount': '100',
	'bottom_thickness': '0.2',
	'hop_on_move': 'False',
	'plugin_config': """(lp1
(dp2
S'params'
p3
(dp4
S'minDeviation'
p5
V0.02
p6
sS'verboseOut'
p7
I0
sS'minSegment'
p8
V0.1
p9
ssS'filename'
p10
S'Simplify.py'
p11
sa.""",
	'object_center_x': '60',
	'object_center_y': '60',
	'platform_adhesion': 'none',
	'brim_enable': 'Off',
	'brim_line_count': '5',
	'add_start_end_gcode': 'True',
	'gcode_extension': 'g',
	'alternative_center': '',
	'clear_z': '0.0',
	'extruder': '0',

	'organic_clip': 'False',
	'clip': '0.0',

	'support': 'None',
	'support_density': '0.3',
	'support_angle': '65',
	'support_extrusion_width': '0.3',

	'bottom_surface_thickness_layers': '2',
	'top_surface_thickness_layers': '3',

	'custom_machine_height': '200',
	'custom_machine_width': '200',
	'custom_machine_depth': '200',

	'vase': 'False',
	'temp_infill': '10',

	'top_surface_flow': '1',

	'edge_width_mm': '0.40',
	'infill_width': '0.4',
	'bridge_feed_ratio': '100',
	'bridge_flow_ratio': '105',
	'perimeter_speed_ratio': '50',
	'skin_speed_ratio': '75',
	'perimeter_flow_ratio': '75',

	'bridge_direction': True,

	'filament_flow': '100',
	'layer0_width_factor': '100',
	'support_type': 'Lines',
	'support_fill_rate': '20',
	'perimeter_before_infill': 'true',
	'fix_horrible_union_all_type_a': 'True',
	'support_xy_distance':'0.6',
	'support_z_distance':'0.15',
	'extra_support_amount':'0',
	#'extruder': '0',
}
# #######################################################################################
# 	'start.gcode': """;Sliced {filename} at: {day} {date} {time}
# ;Basic settings: Layer height: {layer_height} Walls: {wall_thickness} Fill: {fill_density}
# ;Print time: {print_time}
# ;Filament used: {filament_amount}m {filament_weight}g
# ;Filament cost: {filament_cost}
#
#
# ;G92 X0 Y0 Z0 E0         ;reset software position to front/left/z=0.0
#
# ;G92 E0                  ;zero the extruded length
# ;G1 F200 E3              ;extrude 3mm of feed stock
# ;G92 E0                  ;zero the extruded length again
#
# G1 Z0 E0 F2000
# G1 X65 E7 F1500
# G1 X8 Y2 E14 F1500
# G92 E0
# G1 E-3 F1000
# """,

alterationDefault = {
#######################################################################################
	'start.gcode': """;Sliced {filename} at: {day} {date} {time}
;Basic settings:; Layer height: {layer_height} ; Walls: {wall_thickness} ; Fill: {fill_density} ; Speed: {print_speed} ; Temperature: {print_temperature} ; Filament Diameter: {filament_diameter} ; Support Structures: {support} ; Support Angle: {support_angle}
;Print time: {print_time}
;Print weight: {filament_weight}g
G1 Z0.2 E0 F2000
G1 X65 E7 F1500
G1 X12 Y2 E14 F1500
G92 E0
;G1 E-3 F1000
""",
#######################################################################################
	'end.gcode': """;End GCode
M104 S0                     ;extruder heater off
M140 S0                     ;heated bed heater off (if you have it)

G91                                    ;relative positioning
;G1 E-1 F300                            ;retract the filament a bit before lifting the nozzle, to release some of the pressure
;G1 Z+0.5 E-5 X-20 Y-20 F{travel_speed} ;move Z up a bit and retract filament even more
G1 Z0.2 E-4 F2000 ;move Z up a bit and retract filament even more
G4 P600 ; dwell time of 900 ms
G28 X0 Y0                              ;move X/Y to min endstops, so the head is out of the way
G91; use relative
G1 Z80 F3000; drop 80mm
M106 S0; turn off fan

M84                         ;steppers off
G90                         ;absolute positioning
""",
#######################################################################################
	'support_start.gcode': '',
	'support_end.gcode': '',
	'cool_start.gcode': '',
	'cool_end.gcode': '',
	'replace.csv': ';LAYER:1	;LAYER:1	M104 S220',
#######################################################################################
	'nextobject.gcode': """;Move to next object on the platform. clear_z is the minimal z height we need to make sure we do not hit any objects.
G92 E0

G91                                    ;relative positioning
G1 E-1 F300                            ;retract the filament a bit before lifting the nozzle, to release some of the pressure
G1 Z+0.5 E-5 F{travel_speed}           ;move Z up a bit and retract filament even more
G90                                    ;absolute positioning

G1 Z{clear_z} F{max_z_speed}
G92 E0
G1 X{object_center_x} Y{object_center_x} F{travel_speed}
G1 F200 E6
G92 E0
""",
#######################################################################################
	'switchExtruder.gcode': """;Switch between the current extruder and the next extruder, when printing with multiple extruders.
G92 E0
G1 E-15 F5000
G92 E0
T{extruder}
G1 E15 F5000
G92 E0
""",
}
preferencesDefaultSettings = {
	'startMode': 'Normal',
	'lastFile': os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resources', 'example', '20mmCube (5mm tall).stl')),
	'selectedFile': '',
	'machine_width': '215',
	'machine_depth': '160',
	'machine_height': '220',
	
	'machine_type': 'reprap',
	'ultimaker_extruder_upgrade': 'False',
	'has_heated_bed': 'False',
	'extruder_amount': '1',
	'extruder_offset_x1': '0.0',
	'extruder_offset_y1': '0.0',
	'extruder_offset_x2': '0.0',
	'extruder_offset_y2': '0.0',
	'extruder_offset_x3': '0.0',
	'extruder_offset_y3': '0.0',
	'filament_density': '1300',
	'steps_per_e': '0', #not used
	'serial_port': 'AUTO',
	'serial_port_auto': '',
	'serial_baud': 'AUTO',
	'serial_baud_auto': '',
	'slicer': 'CuraEngine',
	'save_profile': 'False',
	'filament_cost_kg': '0',
	'filament_cost_meter': '0',
	'sdpath': '',
	'sdshortnames': 'False',
	'check_for_updates': 'False',
	'window_maximized': 'False',
	'window_pos_x': '0',
	'auto_detect_sd': 'True',
	'window_normal_sash': '',
	
	'machine_center_is_zero': 'False',
	'filament_physical_density': '1300',
	
	'extruder_head_size_min_x': '0.0',
	'extruder_head_size_min_y': '0.0',
	'extruder_head_size_max_x': '0.0',
	'extruder_head_size_max_y': '0.0',
	'extruder_head_size_height': '0.0',
	
	'model_colour': '#2BB673',
	'model_colour2': '#CB3030',
	'model_colour3': '#DDD93C',
	'model_colour4': '#4550D3',

	'show_advanced': 'False',

	'first_run_tour_done': 'False',
}

#########################################################
## Profile and preferences functions
#########################################################

## Profile functions
def getDefaultProfilePath():
	if platform.system() == "Windows":
		basePath = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
		#If we have a frozen python install, we need to step out of the library.zip
		if hasattr(sys, 'frozen'):
			basePath = os.path.normpath(os.path.join(basePath, ".."))
	else:
		basePath = os.path.expanduser('~/.cura/%s' % version.getVersion(False))
	if not os.path.isdir(basePath):
		os.makedirs(basePath)
	return os.path.join(basePath, 'current_profile.ini')
def getBasePath():
	if platform.system() == "Windows":
		basePath = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
		#If we have a frozen python install, we need to step out of the library.zip
		if hasattr(sys, 'frozen'):
			basePath = os.path.normpath(os.path.join(basePath, ".."))
	else:
		basePath = os.path.expanduser('~/.cura/%s' % version.getVersion(False))
	if not os.path.isdir(basePath):
		os.makedirs(basePath)
	return basePath
def loadGlobalProfile(filename):
	#Read a configuration file as global config
	global globalProfileParser
	globalProfileParser = ConfigParser.ConfigParser()
	globalProfileParser.read(filename)

def resetGlobalProfile():
	#Read a configuration file as global config
	global globalProfileParser
	globalProfileParser = ConfigParser.ConfigParser()

	if getPreference('machine_type') == 'ultimaker':
		putProfileSetting('nozzle_size', '0.4')
		if getPreference('ultimaker_extruder_upgrade') == 'True':
			putProfileSetting('retraction_enable', 'True')
	else:
		putProfileSetting('nozzle_size', '0.35')

def saveGlobalProfile(filename):
	#Save the current profile to an ini file
	globalProfileParser.write(open(filename, 'w'))

def loadGlobalProfileFromString(options):
	global globalProfileParser
	globalProfileParser = ConfigParser.ConfigParser()
	globalProfileParser.add_section('profile')
	globalProfileParser.add_section('alterations')
	options = base64.b64decode(options)
	options = zlib.decompress(options)
	(profileOpts, alt) = options.split('\f', 1)
	for option in profileOpts.split('\b'):
		if len(option) > 0:
			(key, value) = option.split('=', 1)
			globalProfileParser.set('profile', key, value)
	for option in alt.split('\b'):
		if len(option) > 0:
			(key, value) = option.split('=', 1)
			globalProfileParser.set('alterations', key, value)

def getGlobalProfileString():
	global globalProfileParser
	if not globals().has_key('globalProfileParser'):
		loadGlobalProfile(getDefaultProfilePath())
	
	p = []
	alt = []
	tempDone = []
	if globalProfileParser.has_section('profile'):
		for key in globalProfileParser.options('profile'):
			if key in tempOverride:
				p.append(key + "=" + tempOverride[key])
				tempDone.append(key)
			else:
				p.append(key + "=" + globalProfileParser.get('profile', key))
	if globalProfileParser.has_section('alterations'):
		for key in globalProfileParser.options('alterations'):
			if key in tempOverride:
				p.append(key + "=" + tempOverride[key])
				tempDone.append(key)
			else:
				alt.append(key + "=" + globalProfileParser.get('alterations', key))
	for key in tempOverride:
		#print key
		if key not in tempDone:
			
			p.append(key + "=" + tempOverride[key])
	ret = '\b'.join(p) + '\f' + '\b'.join(alt)
	ret = base64.b64encode(zlib.compress(ret, 9))
	return ret

def getProfileSetting(name):
	if name in tempOverride:
		return unicode(tempOverride[name], "utf-8")
	#Check if we have a configuration file loaded, else load the default.
	if not globals().has_key('globalProfileParser'):
		loadGlobalProfile(getDefaultProfilePath())
	if not globalProfileParser.has_option('profile', name):
		if name in profileDefaultSettings:
			default = profileDefaultSettings[name]
		else:
			print("Missing default setting for: '" + name + "'")
			profileDefaultSettings[name] = ''
			default = ''
		if not globalProfileParser.has_section('profile'):
			globalProfileParser.add_section('profile')
		globalProfileParser.set('profile', name, str(default))
		#print(name + " not found in profile, so using default: " + str(default))
		return default
	return globalProfileParser.get('profile', name)

def getProfileSettingFloat(name):
	try:
		setting = getProfileSetting(name).replace(',', '.')
		return float(eval(setting, {}, {}))
	except (ValueError, SyntaxError, TypeError):
		return 0.0

def getProfileSettingDefault(name):
	if name in profileDefaultSettings:
		default = profileDefaultSettings[name]
		return default
	else:
		return
def putProfileSetting(name, value):
	#Check if we have a configuration file loaded, else load the default.
	if not globals().has_key('globalProfileParser'):
		loadGlobalProfile(getDefaultProfilePath())
	if not globalProfileParser.has_section('profile'):
		globalProfileParser.add_section('profile')
	globalProfileParser.set('profile', name, str(value))

def isProfileSetting(name):
	if name in profileDefaultSettings:
		return True
	return False

## Preferences functions
global globalPreferenceParser
globalPreferenceParser = None

def getPreferencePath():
	if platform.system() == "Windows":
		basePath = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
		#If we have a frozen python install, we need to step out of the library.zip
		if hasattr(sys, 'frozen'):
			basePath = os.path.normpath(os.path.join(basePath, ".."))
	else:
		basePath = os.path.expanduser('~/.cura/%s' % version.getVersion(False))
	if not os.path.isdir(basePath):
		os.makedirs(basePath)
	return os.path.join(basePath, 'preferences.ini')

def getPreferenceFloat(name):
	try:
		setting = getPreference(name).replace(',', '.')
		return float(eval(setting, {}, {}))
	except (ValueError, SyntaxError, TypeError):
		return 0.0

def getPreferenceColour(name):
	colorString = getPreference(name)
	return [float(int(colorString[1:3], 16)) / 255, float(int(colorString[3:5], 16)) / 255, float(int(colorString[5:7], 16)) / 255, 1.0]

def getPreference(name):
	if name in tempOverride:
		return unicode(tempOverride[name])
	global globalPreferenceParser
	if globalPreferenceParser == None:
		globalPreferenceParser = ConfigParser.ConfigParser()
		globalPreferenceParser.read(getPreferencePath())
	if not globalPreferenceParser.has_option('preference', name):
		if name in preferencesDefaultSettings:
			default = preferencesDefaultSettings[name]
		else:
			print("Missing default setting for: '" + name + "'")
			preferencesDefaultSettings[name] = ''
			default = ''
		if not globalPreferenceParser.has_section('preference'):
			globalPreferenceParser.add_section('preference')
		globalPreferenceParser.set('preference', name, str(default))
		#print(name + " not found in preferences, so using default: " + str(default))
		return default
	return unicode(globalPreferenceParser.get('preference', name), "utf-8")

def putPreference(name, value):
	#Check if we have a configuration file loaded, else load the default.
	global globalPreferenceParser
	if globalPreferenceParser == None:
		globalPreferenceParser = ConfigParser.ConfigParser()
		globalPreferenceParser.read(getPreferencePath())
	if not globalPreferenceParser.has_section('preference'):
		globalPreferenceParser.add_section('preference')
	globalPreferenceParser.set('preference', name, unicode(value).encode("utf-8"))
	globalPreferenceParser.write(open(getPreferencePath(), 'w'))

def isPreference(name):
	if name in preferencesDefaultSettings:
		return True
	return False

## Temp overrides for multi-extruder slicing and the project planner.
tempOverride = {}
def setTempOverride(name, value):
	tempOverride[name] = unicode(value).encode("utf-8")
def clearTempOverride(name):
	del tempOverride[name]
def resetTempOverride():
	tempOverride.clear()

#########################################################
## Utility functions to calculate common profile values
#########################################################
def calculateEdgeWidth():
	wallThickness = getProfileSettingFloat('wall_thickness')
	nozzleSize = getProfileSettingFloat('nozzle_size')

	return nozzleSize
	
	if wallThickness < nozzleSize:
		return wallThickness

	lineCount = float(wallThickness / nozzleSize + 0.0001)
	lineWidth = wallThickness / lineCount
	lineWidthAlt = wallThickness / (lineCount + 1)
	if lineWidth > nozzleSize * 1.5:
		print lineWidthAlt
		return lineWidthAlt
	# return 2.0*0.2 #justin
	# return 0.35 #justin
	return lineWidth

def calculateLineCount():
	wallThickness = getProfileSettingFloat('wall_thickness')
	nozzleSize = getProfileSettingFloat('nozzle_size')
	
	if wallThickness < nozzleSize:
		return 1
	else:
		return int(wallThickness)
	lineCount = int(wallThickness / nozzleSize + 0.0001)
	lineWidth = wallThickness / lineCount
	lineWidthAlt = wallThickness / (lineCount + 1)
	if lineWidth > nozzleSize * 1.5:
		return lineCount + 1
	return lineCount

def calculateSolidLayerCount():
	layerHeight = getProfileSettingFloat('layer_height')
	solidThickness = getProfileSettingFloat('solid_layer_thickness')
	return int(math.ceil(solidThickness / layerHeight - 0.0001))
def calculateObjectSizeOffsets():
	size = 0.0

	if getProfileSetting('brim_enable') == 'Enabled':
		size += getProfileSettingFloat('brim_line_count') * calculateEdgeWidth()
	elif getProfileSetting('platform_adhesion') == 'Raft':
		pass
	else:
		if getProfileSettingFloat('skirt_line_count') > 0:
			size += getProfileSettingFloat('skirt_line_count') * calculateEdgeWidth() + getProfileSettingFloat('skirt_gap')

	#if getProfileSetting('enable_raft') != 'False':
	#	size += profile.getProfileSettingFloat('raft_margin') * 2
	#if getProfileSetting('support') != 'None':
	#	extraSizeMin = extraSizeMin + numpy.array([3.0, 0, 0])
	#	extraSizeMax = extraSizeMax + numpy.array([3.0, 0, 0])
	return [size, size]
def getMachineCenterCoords():
	return [getPreferenceFloat('machine_width') / 2.0, getPreferenceFloat('machine_depth') / 2.0]
#########################################################
## Alteration file functions
#########################################################
def replaceTagMatch(m):
	pre = m.group(1)
	tag = m.group(2)
	if tag == 'time':
		return pre + time.strftime('%H:%M:%S').encode('utf-8', 'replace')
	if tag == 'date':
		return pre + time.strftime('%d %b %Y').encode('utf-8', 'replace')
	if tag == 'day':
		return pre + time.strftime('%a').encode('utf-8', 'replace')
	if tag == 'print_time':
		return pre + '#P_TIME#'
	if tag == 'filament_amount':
		return pre + '#F_AMNT#'
	if tag == 'filament_weight':
		return pre + '#F_WGHT#'
	if tag == 'filament_cost':
		return pre + '#F_COST#'
	if pre == 'F' and tag in ['print_speed', 'retraction_speed', 'travel_speed', 'max_z_speed', 'bottom_layer_speed', 'cool_min_feedrate']:
		f = getProfileSettingFloat(tag) * 60
	elif tag == 'support':
		f = getProfileSetting(tag)
	elif isProfileSetting(tag):
		f = getProfileSettingFloat(tag)
	elif isPreference(tag):
		f = getProfileSettingFloat(tag)
	else:
		return '%s?%s?' % (pre, tag)
	try:
		if (f % 1) == 0:
			return pre + str(int(f))
	except TypeError:
		pass
	return pre + str(f)

def replaceGCodeTags(filename, gcodeInt):
	f = open(filename, 'r+')
	data = f.read(2048)
	data = data.replace('#P_TIME#', ('%5d:%02d' % (int(gcodeInt.totalMoveTimeMinute / 60), int(gcodeInt.totalMoveTimeMinute % 60)))[-8:])
	data = data.replace('#F_AMNT#', ('%8.2f' % (gcodeInt.extrusionAmount / 1000))[-8:])
	data = data.replace('#F_WGHT#', ('%8.2f' % (gcodeInt.calculateWeight() * 1000))[-8:])
	# cost = gcodeInt.calculateCost()
	# if cost == False:
	# 	cost = 'Unknown'
	# data = data.replace('#F_COST#', ('%8s' % (cost.split(' ')[0]))[-8:])
	f.seek(0)
	f.write(data)
	f.close()

### Get aleration raw contents. (Used internally in Cura)
def getAlterationFile(filename):
	#Check if we have a configuration file loaded, else load the default.
	if not globals().has_key('globalProfileParser'):
		loadGlobalProfile(getDefaultProfilePath())
	
	if not globalProfileParser.has_option('alterations', filename):
		if filename in alterationDefault:
			default = alterationDefault[filename]
		else:
			print("Missing default alteration for: '" + filename + "'")
			alterationDefault[filename] = ''
			default = ''
		if not globalProfileParser.has_section('alterations'):
			globalProfileParser.add_section('alterations')
		#print("Using default for: %s" % (filename))
		globalProfileParser.set('alterations', filename, default)
	return unicode(globalProfileParser.get('alterations', filename), "utf-8")

def setAlterationFile(filename, value):
	#Check if we have a configuration file loaded, else load the default.
	if not globals().has_key('globalProfileParser'):
		loadGlobalProfile(getDefaultProfilePath())
	if not globalProfileParser.has_section('alterations'):
		globalProfileParser.add_section('alterations')
	globalProfileParser.set('alterations', filename, value.encode("utf-8"))
	saveGlobalProfile(getDefaultProfilePath())

### Get the alteration file for output. (Used by Skeinforge)
def getAlterationFileContents(filename):
	prefix = ''
	postfix = ''
	alterationContents = getAlterationFile(filename)
	if filename == 'start.gcode':
		#For the start code, hack the temperature and the steps per E value into it. So the temperature is reached before the start code extrusion.
		#We also set our steps per E here, if configured.
		#eSteps = getPreferenceFloat('steps_per_e')
		prefix += _(';Sliced with Tinkerine Suite version ') + version.getVersion() + '\n'
		prefix += 'M104 S220\n'
		prefix += 'T0\n'
		prefix += 'G28\n'
		prefix += 'G90\n'
		# prefix += 'M83\n' ;for relative extruder movements
		prefix += 'M106 S0\n'
		prefix += 'G92 E0\n'
		prefix += 'G1 Z0.5 F2000\n'
		#if eSteps > 0:
		#	prefix += 'M92 E%f\n' % (eSteps)
		temp = getProfileSettingFloat('print_temperature') + 10
		if temp > 230:
			temp = 230
		print_temp = getProfileSettingFloat('print_temperature')
		bedTemp = 0
		if getPreference('has_heated_bed') == 'True':
			bedTemp = getProfileSettingFloat('print_bed_temperature')
		
		if bedTemp > 0 and not '{print_bed_temperature}' in alterationContents:
			prefix += 'M140 S%f\n' % (bedTemp)
		# if temp > 0 and not '{first_layer_print_temperature}' in alterationContents:
		if temp > 0:
			prefix += 'M109 S%f\n' % (temp)
			#prefix += 'M109 215'
		if bedTemp > 0 and not '{print_bed_temperature}' in alterationContents:
			prefix += 'M190 S%f\n' % (bedTemp)
		#prefix += 'G1 Z0 F2000\n'
		#prefix += 'G92 E0\n'
		#prefix += 'G1 X65 E7 F2000\n'
		#prefix += 'G1 X0 Y2 E14 F2000\n'
		#prefix += 'G92 E0\n'

	elif filename == 'end.gcode':
		#Append the profile string to the end of the GCode, so we can load it from the GCode file later.
		#postfix = ';CURA_PROFILE_STRING:%s\n' % (getGlobalProfileString())
		postfix = ';'
	elif filename == 'replace.csv':
		#Always remove the extruder on/off M codes. These are no longer needed in 5D printing.
		prefix = 'M101\nM103\n'
	elif filename == 'support_start.gcode' or filename == 'support_end.gcode':
		#Add support start/end code 
		if getProfileSetting('support_dual_extrusion') == 'True' and int(getPreference('extruder_amount')) > 1:
			if filename == 'support_start.gcode':
				setTempOverride('extruder', '1')
			else:
				setTempOverride('extruder', '0')
			alterationContents = getAlterationFileContents('switchExtruder.gcode')
			clearTempOverride('extruder')
		else:
			alterationContents = ''
	return unicode(prefix + re.sub("(.)\{([^\}]*)\}", replaceTagMatch, alterationContents).rstrip() + '\n' + postfix).strip().encode('utf-8')

###### PLUGIN #####

def getPluginConfig():
	try:
		return pickle.loads(getProfileSetting('plugin_config'))
	except:
		return []

def setPluginConfig(config):
	putProfileSetting('plugin_config', pickle.dumps(config))

def getPluginBasePaths():
	ret = []
	if platform.system() != "Windows":
		ret.append(os.path.expanduser('~/.cura/plugins/'))
	if platform.system() == "Darwin" and hasattr(sys, 'frozen'):
		ret.append(os.path.normpath(os.path.join(resources.resourceBasePath, "Cura/plugins")))
	else:
		ret.append(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'plugins')))
	return ret

def getPluginList():
	ret = []
	for basePath in getPluginBasePaths():
		for filename in glob.glob(os.path.join(basePath, '*.py')):
			filename = os.path.basename(filename)
			if filename.startswith('_'):
				continue
			with open(os.path.join(basePath, filename), "r") as f:
				item = {'filename': filename, 'name': None, 'info': None, 'type': None, 'params': []}
				for line in f:
					line = line.strip()
					if not line.startswith('#'):
						break
					line = line[1:].split(':', 1)
					if len(line) != 2:
						continue
					if line[0].upper() == 'NAME':
						item['name'] = line[1].strip()
					elif line[0].upper() == 'INFO':
						item['info'] = line[1].strip()
					elif line[0].upper() == 'TYPE':
						item['type'] = line[1].strip()
					elif line[0].upper() == 'DEPEND':
						pass
					elif line[0].upper() == 'PARAM':
						m = re.match('([a-zA-Z]*)\(([a-zA-Z_]*)(?::([^\)]*))?\) +(.*)', line[1].strip())
						if m is not None:
							item['params'].append({'name': m.group(1), 'type': m.group(2), 'default': m.group(3), 'description': m.group(4)})
					else:
						print "Unknown item in effect meta data: %s %s" % (line[0], line[1])
				if item['name'] != None and item['type'] == 'postprocess':
					ret.append(item)
	return ret

def runPostProcessingPlugins(gcodefilename):
	pluginConfigList = getPluginConfig()
	pluginList = getPluginList()
	
	for pluginConfig in pluginConfigList:
		plugin = None
		for pluginTest in pluginList:
			if pluginTest['filename'] == pluginConfig['filename']:
				plugin = pluginTest
		if plugin is None:
			continue
		
		pythonFile = None
		for basePath in getPluginBasePaths():
			testFilename = os.path.join(basePath, pluginConfig['filename'])
			if os.path.isfile(testFilename):
				pythonFile = testFilename
		if pythonFile is None:
			continue
		
		locals = {'filename': gcodefilename}
		for param in plugin['params']:
			value = param['default']
			if param['name'] in pluginConfig['params']:
				value = pluginConfig['params'][param['name']]
			
			if param['type'] == 'float':
				try:
					value = float(value)
				except:
					value = float(param['default'])
			
			locals[param['name']] = value
		try:
			execfile(pythonFile, locals)
		except:
			locationInfo = traceback.extract_tb(sys.exc_info()[2])[-1]
			return "%s: '%s' @ %s:%s:%d" % (str(sys.exc_info()[0].__name__), str(sys.exc_info()[1]), os.path.basename(locationInfo[0]), locationInfo[2], locationInfo[1])
	return None

def getSDcardDrives():
	drives = ['']
	if platform.system() == "Windows":
		from ctypes import windll
		bitmask = windll.kernel32.GetLogicalDrives()
		for letter in string.uppercase:
			if bitmask & 1:
				drives.append(letter + ':/')
			bitmask >>= 1
	if platform.system() == "Darwin":
		drives = []
		for volume in glob.glob('/Volumes/*'):
			if stat.S_ISLNK(os.lstat(volume).st_mode):
				continue
			drives.append(volume)
	return drives
