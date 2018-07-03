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
#dictionary holding asns as keys to AS values
asnDict = {} 
#array holding object data of links from file
links = []
#maximum size of a visualized asn
MAX_SIZE = 18
#method to print how to run script

selected_key = "customer_cone_asnes";

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
	links = jsonl_load(fname)
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
	global links
	#count of asns with no longitude
	noLongitude = 0
	#count of invalid links
	invalidLinks = 0
	#bounds for graph
	min_x = 0
	min_y = 0
	max_x = 0
	max_y = 0
	#max value for radius calculation
	max_value = 0
	#find the max value among all ASNs to calculate radius 
	num_asn_skipped = 0
	asIndex = 0
	while asIndex < len(asns):
            AS = asns[asIndex]  
            if "longitude" not in AS or selected_key not in AS:
                num_asn_skipped += 1
                temp = asns.pop();
                if asIndex < len(asns):
                    asns[asIndex] = temp
                continue
            else:
                asIndex += 1
                value = AS[selected_key];
                if value > max_value:
                    max_value = value

	print ("numNodes:", len(asns),"numSkipped:",num_asn_skipped)
	print ("maxValue:", max_value,)

	if verbose:
            print("Assigning coordinates to nodes")
	for AS in asns:
            value = AS["customer_cone_asnes"]
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
            #add AS object to dictionary
            asnDict[AS["asn"]] = AS


	#increase min max x y slightly, move all ASNes to adjust 
	min_x += min_x*.05
	min_y += min_y*.05
	for AS in asns:
            AS["x"] -= min_x
            AS["y"] -= min_y
	max_x -= min_x
	max_y -= min_y
	min_x = min_y = 0

	#link stuff
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
	if verbose:
            print("Assigning coordinates to links (num links:",len(links),")")
	linkIndex = 0
	num_links_skipped = 0;
	while linkIndex < len(links):
            link = links[linkIndex]
            as1 = asSearch(link["asn0"])
            as2 = asSearch(link["asn1"])
            #create pair of AS objects using asn number data in link
            if as1 is None or as2 is None:
                num_links_skipped += 1
                temp = links.pop()
                if linkIndex < len(links):
                    links[linkIndex] = temp
                continue 
                
            for AS in [as1, as2]: 
                value = AS[selected_key]
                if selected_key not in link:
                    link[selected_key] = value
                elif value > link[selected_key]:
                    link[selected_key] = value

            linkIndex += 1
            #find greatest value in the pair and assign to link
            #get coordinates
            #get information to draw line
            size1 = as1["size"]
            size2 = as2["size"]
            #center xy coordinates on the nodes
            link["x1"] = as1["x"]+ (size1 / 2)
            link["y1"] = as1["y"]+ (size1 / 2)
            link["x2"] = as2["x"]+ (size2 / 2)
            link["y2"] = as2["y"]+ (size2 / 2) 
            #calculate distance for sorting
            link["distance"] = math.sqrt(math.pow(link["x2"] - link["x1"], 2) + math.pow(link["y2"] - link["y1"], 2)) 
            #calculate color
            value = link["customer_cone_asnes"]
            link["color"] = Value2Color(value/max_value)

	#sort links array by distance in descending order
	newLinks = sorted(links, key = lambda link: link["distance"],reverse=True)
	links = newLinks

	print ("Links with skipped ASNs:" + str(num_links_skipped))
	return min_x, min_y, max_x, max_y, max_value

#helper method to search for AS using number from link
def asSearch(asNum):
    if asNum not in asnDict:
        return None
    else:
        return asnDict[asNum]
	
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
	rgbList = hsv2rgb(360*hue, sat, bri)

	''' old ported hexcode - not applicable for cairo
	for v in (r, g, b):
		v = int(v) 
		v = "%x" % int(v)
		if (len(v) < 2):
			v = "0"+ v
	'''
	#convert values to floating point to use with cairo
	index = 0
	while index < len(rgbList): 
		v = rgbList[index]
		rgbList[index] = float(v / 255)
		index += 1
	return (rgbList[0], rgbList[1], rgbList[2])
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
	return [r, g, b]
#method to print the visualization onto an image
def PrintGraph(min_x, min_y, max_x, max_y, max_value):
	# Make calls to PyCairo
	#set up drawing area
	scale = 0.75
	WIDTH = int(max_x) 
	HEIGHT = int(max_y) 
	surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
	cr = cairo.Context(surface)
	cr.translate(WIDTH * (1- scale) / 2, HEIGHT * (1 - scale) / 2) 

	PrintHeader(cr, min_x,min_y,max_x,max_y)
	PrintLinks(cr, max_value, scale)
	PrintNodes(cr, scale)

	# We do not need suppport for this now
	#if (defined $name_file) {
	#    PrintNames(@nodes);
	#}
	##if (defined $print_key) {
	#$max_x = PrintKey($max_x,$max_y, $max_value);
	#}
	#PrintEnder();
	surface.write_to_png("graph3.png") 
	return
#helper method for printGraph to print the header onto the image
def PrintHeader(cr, min_x,min_y,max_x,max_y):
   	return
#helper method for printGraph to print the links onto the image
def PrintLinks(cr, max_value, scale):
	seen = set()
	for link in links:
		x1 = link["x1"] * scale
		y1 = link["y1"] * scale
		x2 = link["x2"] * scale
		y2 = link["y2"] * scale
		color = link["color"]
		linkInfo = ("links", x1, y1, x2, y2, color)
		#skip if is duplicate
		if linkInfo not in seen:
			seen.add(linkInfo)			
			#draw line
			cr.move_to(x1,y1)
			cr.line_to(x2, y2)
			cr.set_source_rgb(color[0], color[1], color[2])
			cr.set_line_width(0.5)
			cr.stroke()			
	return
#helper method for printGraph to print the nodes onto the image
def PrintNodes(cr, scale):
	seen = set()
	for AS in asns:
		#calculate coordinates and get colors
		x = AS["x"] * scale 
		y = AS["y"] * scale
		#decrease size so that dots arent too big 
		size = AS["size"] * scale 
		color = AS["color"]
		nodeInfo = ("nodes", size, x, y, color)
		#skip if is duplicate
		if nodeInfo not in seen:
			seen.add(nodeInfo)
			#save current context with no path
			cr.save()
			#plot point
			#cr.arc(x+size, y + size ,size, 0, 2*math.pi)
			cr.rectangle(x, y, size, size)
			#fill with color 
			cr.set_source_rgb(color[0], color[1], color[2])
			cr.fill_preserve()
			#outline	
			cr.set_source_rgb(0, 0, 0)
			cr.set_line_width(2)
			cr.stroke()
			#restore to saved context to wipe path
			cr.restore()
	return
#run the main method
main(sys.argv[1:])
