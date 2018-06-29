#!  /usr/bin/env python3
import argparse
import sys
import math
import json
import cairo

#boolean controlling whether to print messages about run status
verbose = False
#boolean controlling grayscale of image printed
grayscale = False
#array holding object data of asns from file
asns = []
#array holding object data of links from file
links = []
#maximum size of a visualized asn
MAX_SIZE = 18
#method to print how to run script
def print_help():
	print (sys.argv[0],"-l links.jsonl -a asns.jsonl")
#main method
def main(argv):
	global verbose
	parser = argparse.ArgumentParser()
	parser.add_argument("-l", type=str, dest="links", help="loads in the asn links file")
	parser.add_argument("-a", type=str, dest="asns", help="loads in the asn links file")
	parser.add_argument("-v", dest="verbose", help="prints out lots of messages", action="store_true")
	args = parser.parse_args()

	if args.links is None or args.asns is None:
		print_help()
		sys.exit()

	if args.verbose:
		verbose = True

	ParseAsns(args.asns)
	ParseLinks(args.links)

	min_x, min_y, max_x, max_y, max_value = SetUpPosition()
	PrintGraph(min_x, min_y, max_x, max_y, max_value)
###########################
#method to populate links array with object data from links file
def ParseLinks(fname):
	global verbose
	global asns
	global links
	if verbose:
		print ("loading",fname)
#method to populate asn array with object data from asn file
def ParseAsns(fname):
	global verbose
	global asns
	if verbose:
		print ("loading",fname)
	asns = jsonl_load(fname)
#helper method for jsonl_load method to create handler for file
def open_safe(filename,op):
	try:
		return open(filename,op)

	except IOError as e:
		traceback.print_stack()
		print ("I/O error({0}): {1} ".format(e.errno, e.strerror), '"'+filename+'"')
		exit()
#method to pull json data from a file
def jsonl_load(filename):
	objects = []
	handle = open_safe(filename,"r")
	decoder = json.JSONDecoder()
	for line in handle:
		if len(line) > 0 and line[0][0] != "#":
			objects.append(decoder.decode(line))
	return objects
###########################
#method to determine positions of all asn nodes and links based on data
def SetUpPosition():
	#count of asns with no longitude
	noLongitude = 0
	#bounds for graph
	min_x = 0
	min_y = 0
	max_x = 0
	max_y = 0
	#max value for radius calculation
	max_value = 0
	#find the max value among all ASNs to calculate radius 
	for AS in asns:
		if "customer_cone_asnes" not in AS:
			value = AS["customer_cone_asnes"] = 0
		else:	
			value = AS["customer_cone_asnes"]
		if value > max_value:
			max_value = value
	print("maxValue:" + str(max_value) + "\n")

	for AS in asns:
		value = AS["customer_cone_asnes"]
		#debugging - can remove later 
		print(value)
		#if asn has no longitude data, skip it and increment count 
		if "longitude" not in AS:
			noLongitude += 1
			asns.remove(AS)
			continue
		#else perform angle calculation to determine location		
		else:
			angle = -2 * 3.14 * AS["longitude"] / 360
		radius = (math.log(max_value+1) - math.log(value+1) +.5)*100
		size = int((MAX_SIZE-3)* (math.log(value+1)/math.log(max_value+1)) )+3;
		#calculate new x using polar coordinate math
		x = radius * math.cos(angle)
		#adjust min and max x based on new X
		if min_x == 0:
			min_x = x 
			max_x = size + x
		elif x < min_x:
			min_x = x
		elif x+size > max_x:
			max_x = x+size
		#calculate new Y using polar coordinate math
		y = radius * math.sin(angle)
		#adjust min and max y based on new Y
		if min_y == 0:
			min_y = y
			max_x = size + x
		elif y < min_y:
			min_y = y
		elif y+size > max_y: 
			max_y = y+size
		#add new values to AS object 
		AS["x"] = x
		AS["y"] = y
		AS["size"] = size
		AS["color"] = Value2Color(value/max_value)
	#increase min max x y slightly, move all ASNes to adjust 
	min_x += min_x*.05
	min_y += min_y*.05
	for AS in asns:
		AS["x"] -= min_x
		AS["y"] -= min_y
	max_x -= min_x
	max_y -= min_y
	min_x = min_y = 0

	#link stuff convert later
	'''
	foreach my $link (keys %link2rec) {
	my $from = $link2rec{$link}{from};
	my $to = $link2rec{$link}{to};
	foreach my $as ($from, $to) {
		foreach my $type (keys %{$as2rec{$as}}) {
			my $value = $as2rec{$as}{$type};
			my $current = $link2rec{$link}{$type};
			if (!defined $current || $current > $value) {
				$link2rec{$link}{$type} = $value;
			}
		}
	}
	my $value = $link2rec{$link}{$type_sort};
	$link2rec{$link}{color} = Value2Color($value/$max_value);
	}
	'''
	print ("ASNs with no longitude:" + str(noLongitude))
	return min_x, min_y, max_x, max_y, max_value
#method to determine the color of a link/node on the visualization
def Value2Color(newValue):
	value = newValue
	hue = 0
	sat = 0
	bri = 0
	#keep value greater than 0.000001
	if (value <= 0.000001):
		value = .000001
	temp = math.log( (120*value)+1)/math.log(121)
	if not grayscale:
		hue = (4+5*temp)/8
		sat = 100
		bri = 100
	else:
		hue = 1
		sat = 100*temp
		bri = 80*temp+20
	#get rgb based on provided data
	(r, g, b) = hsv2rgb(360*hue, sat, bri)
	#create hexcode string 
	for v in (r, g, b): 
		v = "%x" % int(v)
		if (len(v) < 2):
			v = "0"+ v
	return str(r + g + b)
#helper method for Value2Color to determine color of a link/node on the visualization
def hsv2rgb (newH, newS, newV):  
	h = newH
	s = newS
	v = newV

	r = 0
	g = 0
	b = 0
	#keep hue between 0 and 360
	if h < 0:
		h = 0
	if h >= 360:
		h -= 360 
	h /= 60
	
	f = (h - int(h)) * 255;

	s /= 100
	v /= 100
	#change rgb based on hue
	if (int(h) == 0):
		r = v * 255;
		g = v * (255 - (s * (255 - f)))
		b = v * 255 * (1 - s)
	if (int(h) == 1):
		r = v * (255 - s * f)
		g = v * 255;
		b = v * 255 * (1 - s)
	if (int(h) == 2): 
		r = v * 255 * (1 - s)
		g = v * 255;
		b = v * (255 - (s * (255 - f)))
	if (int(h) == 3): 
		r = v * 255 * (1 - s)
		g = v * (255 - s * f)
		b = v * 255
	if (int(h) == 4):
		r = v * (255 - (s * (255 - f)))
		g = v * (255 * (1 - s))
		b = v * 255
	if (int(h) == 5):
		r = v * 255;
		g = v * 255 * (1 - s)
		b = v * (255 - s * f)
	return (r, g, b)
#method to print the visualization onto an image
def PrintGraph(min_x, min_y, max_x, max_y, max_value):
	# Make calls to PyCairo
	#set up drawing area
	WIDTH = int(max_x)
	HEIGHT = int(max_y)
	surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, HEIGHT, HEIGHT)
	cr = cairo.Context(surface)
	cr.scale(HEIGHT, HEIGHT)

	PrintHeader(cr, min_x,min_y,max_x,max_y)
	PrintLinks(cr, max_value)
	PrintNodes(cr, max_x, max_y)

	# We do not need suppport for this now
	#if (defined $name_file) {
	#    PrintNames(@nodes);
	#}
	##if (defined $print_key) {
	#$max_x = PrintKey($max_x,$max_y, $max_value);
	#}
	#PrintEnder();
	surface.write_to_png("graph.png") 
	return
#helper method for printGraph to print the header onto the image
def PrintHeader(cr, min_x,min_y,max_x,max_y):
   	return
#helper method for printGraph to print the links onto the image
def PrintLinks(cr, max_value):
	return
#helper method for printGraph to print the nodes onto the image
def PrintNodes(cr, max_x, max_y):
	for AS in asns:
		#calculate coordinates and get colors
		x = AS["x"]/max_x
		y = AS["y"]/max_y
		size = AS["size"]/max_x
		color = AS["color"]
		#plot point
		cr.arc(x+size, y + size ,size, 0, 2*math.pi)
		#set color later	
		cr.set_source_rgb(0, 0, 1)
		cr.fill()
	return
#run the main method
main(sys.argv[1:])
