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
asn_dict = {} 
#array holding object data of links from file
links = []
#maximum size of a visualized asn
MAX_SIZE = 18
#current metric being used to create visualization
selected_key = "customer_cone_asnes"

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
    #bounds for graph
    min_x = 0
    min_y = 0
    max_x = 0
    max_y = 0
    #max value for radius calculation
    max_value = 0
    #number of asns skipped because of missing data
    num_asn_skipped = 0
    #index for traversing through asn list
    asIndex = 0
    while asIndex < len(asns): 
        AS = asns[asIndex]
        if "longitude" not in AS or selected_key not in AS:
            num_asn_skipped += 1
            #pop last AS from end of list
            temp = asns.pop();
            #if not at the end of the list
            if asIndex < len(asns):
                #replace the asn at current position with last asn
                asns[asIndex] = temp
                continue
        else:	
            #check for max value
            value = AS[selected_key]
            if value > max_value:
                max_value = value
            #move loop forward
            asIndex += 1
    print("maxValue:" + str(max_value) + "\n")

    if verbose:
        print("Assigning coordinates to nodes (num nodes:",len(asns),")")
    #loop through current asn list, calculating and adding coordinates to each asn  
    for AS in asns:
        value = AS[selected_key]	
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
        asn_dict[AS["asn"]] = AS

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
    if verbose:
        print("Assigning coordinates to links (num links:",len(links),")")

    #number of links skipped because of skipped asn
    num_links_skipped = 0;
    #index for traversing through link list  
    linkIndex = 0
    #loop through links, removing links with skipped asn and assigning coordinates to others
    while linkIndex < len(links):
        #move loop forward
        link = links[linkIndex]
        #create pair of AS objects using asn number data in link
        as1 = asSearch(link["asn0"])
        as2 = asSearch(link["asn1"])
        #if either AS is invalid, skip to next iteration
        if as1 is None or as2 is None:
            num_links_skipped += 1
            temp = links.pop()
            #if not at end of list
            if linkIndex < len(links):
                #replace link at current position with lastl ink in list
                links[linkIndex] = temp
            continue
        as_pair = (as1, as2)
        #find greatest value in the pair and assign to link
        for AS in as_pair:
            value = AS[selected_key]
            if selected_key not in link:
                link[selected_key] = value
            elif value > link[selected_key]:
                link[selected_key] = value
		
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
        value = link[selected_key]
        link["color"] = Value2Color(value/max_value)
        linkIndex += 1

    #sort links array by distance in descending order
    new_links = sorted(links, key = lambda link: link["distance"],reverse=True)
    links = new_links


    print ("numNodes:", len(asns),"numSkipped:",num_asn_skipped)
    print ("numLinks:", len(links),"numSkipped:",num_links_skipped) 
    return min_x, min_y, max_x, max_y, max_value
#helper method to search for AS using number from link
def asSearch(asNum):
    if asNum not in asn_dict:
        return None
    else:
	    return asn_dict[asNum]

	
#method to determine the color of a link/node on the visualization
def Value2Color(new_value):
    value = new_value
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
    rgb_list = hsv2rgb(360*hue, sat, bri)

    #convert values to floating point to use with cairo
    index = 0
    while index < len(rgb_list): 
        v = rgb_list[index]
        rgb_list[index] = float(v / 255)
        index += 1
    return (rgb_list[0], rgb_list[1], rgb_list[2])
#helper method for Value2Color to determine color of a link/node on the visualization
def hsv2rgb (new_h, new_s, new_v):  
    h = new_h
    s = new_s
    v = new_v

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
    scale = 1
    WIDTH = int(max_x * 1.6) 
    HEIGHT = int(max_y * 1.5) 
    
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    cr = cairo.Context(surface)
    
	
	
	
    PrintHeader(cr, min_x,min_y,max_x,max_y)
    PrintKey(cr, max_x, max_y, max_value, scale)
    cr.translate(WIDTH * (1 - scale) / 2, HEIGHT * (1 / 3) / 2) 
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
    surface.write_to_png("graph4.png") 
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
#helper method for printGraph to print the color key onto the image
def PrintKey(cr, new_max_x, new_max_y, new_max_value, scale):
    max_x = new_max_x * 1.5
    max_y = new_max_y * 1.5
    max_value = new_max_value

    key_width = max_x / 40 
    key_x_margin = key_width * 0.1
    key_x = max_x - key_width - key_x_margin 
    #max_x = max_x + key_x_margin + key_width

    key_height = 6 * max_y / 10 
    key_y = (max_y - key_height) / 2
	
    num_bars = 200
    if max_value > 0 and max_value < num_bars:
        num_bars = max_value
    for value in range(201):
        fraction = value/num_bars
        color = Value2Color(fraction)
        x = key_x
        width = key_width
        y = key_y
        height = key_height * (1 - fraction) 
		
        cr.rectangle(x, y, width, height)
        cr.set_source_rgb(color[0], color[1], color[2])
        cr.fill()
    #border
    cr.rectangle(key_x, key_y, key_width, key_height)
    cr.set_line_width(5)
    cr.set_source_rgb(0,0,0)
    cr.stroke()
    
    cr.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, 
    cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(50)
    cr.set_source_rgb(0, 0, 0)
    for value in range(11):
        fraction = value / 10
        number = ("%d" % (max_value * fraction))
        x1 = key_x 
        y1 = (key_y + key_height * (1 - fraction))

        x2 = (key_x + key_width + 2 * key_x_margin) 
        y2 = y1

		
        cr.move_to(x1,y1)
        cr.line_to(x2, y2)
        cr.set_source_rgb(0, 0, 0)
        cr.set_line_width(2)
        cr.stroke()
        
        cr.move_to(x2, y2)
        cr.line_to(x2 + 50, y2)
        cr.show_text(number)
#run the main method
main(sys.argv[1:])
