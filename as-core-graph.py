#!  /usr/bin/env python3
import argparse
import sys
import math
import json
import cairo
import urllib.request
import urllib.parse
import urllib.error
import re

#boolean controlling whether to print messages about run status
verbose = False
#boolean controlling grayscale of image printed
grayscale = False
#boolean controlling whether to print color key on image
print_key = False
#number of the asn to focus on with fisheye effect
#focus_asn = -1 
#array holding object data of asns from file
asns = []
#dictionary holding asns as keys to AS values
asn_dict = {} 
#array holding object data of links from file
links = []
#maximum size of a visualized asn
MAX_SIZE = 18
#drawing mode of graph
drawing_mode = "full" 
#target AS to focus on 
target_AS = set()
#Name of output file to write graph to
output_file = "as-core.png"
#file format of output file to write graph to
file_format = "PNG"
#current metric being used to create visualization
selected_key = "customer_cone_asnes"
#function to retrieve the metric value from AS
key_function = None
#smallest value to print name of AS
name_filter = 200

#method to print how to run script
def print_help():
    print (sys.argv[0],"-u as-rank.caida.org/api/v1")
#main method
def main(argv):
    global verbose
    global print_key
    global key_function
    global focus_asn
    global drawing_mode
    global links
    global asns
    global target_AS
    global output_file
    global file_format
   
    parser = argparse.ArgumentParser()
    #parser.add_argument("-l", type=str, dest="links", help="loads in the asn links file")
    #parser.add_argument("-a", type=str, dest="asns", help="loads in the asn links file")   
    #parser.add_argument("-f", type=int, nargs='?', const=-1, dest="focus", help="number of AS to focus on using fisheye effect")
    parser.add_argument("-u", type=str, dest="url", help="loads in the API url")
    parser.add_argument("-k", dest="print_key", help="prints out color key for visualization", action="store_true")
    parser.add_argument("-v", dest="verbose", help="prints out lots of messages", action="store_true")
    parser.add_argument("-F", default=None, dest="first_page", help="draw only the first page of links", action="store_true")
    parser.add_argument("-t", type=str, default=None, nargs='?', const="", dest="target", help="asns to display neighbors of, separated by comma") 
    parser.add_argument("-s", type=str, default=None, nargs='?', const="", dest="link_asns", help="ASnes of a single link, separated by comma")
    parser.add_argument("-o", type=str, default=None, nargs='?', const="", dest="org_name", help="Organization name of members to focus on")
    parser.add_argument("-O", type=str, default=None, nargs='?', const="", dest="output_file", help="Name of output file to write graph to")
    parser.add_argument("-f", type=str, default="PNG", nargs='?', const="", dest="file_format", choices=["SVG","PDF","PNG"], help="file format of output file to write graph to")
    args = parser.parse_args()

    if args.url is None:
        print_help()
        sys.exit()
    '''
    if args.focus is not None:
        if args.focus > -1:
            focus_asn = args.focus
        else: 
            print_help()
            sys.exit()
    '''
    if args.print_key:
        print_key = True

    if args.verbose:
        verbose = True

    if args.first_page is not None:
        if args.first_page:
            if drawing_mode == "full":
                drawing_mode = "first_page"
                ParseFirstPage(args.url)
   
    if args.target is not None:
        if args.target != "":
            if drawing_mode == "full": 
                drawing_mode = "target"     
                target_list = args.target.split(",")
                target_AS = ParseTargetLinks(args.url, target_list)
        else: 
            print_help()
            sys.exit()

    if args.link_asns is not None:
        if args.link_asns != "":  
            if drawing_mode == "full":
                drawing_mode = "single_link" 
                ParseSingleLink(args.url, args.link_asns)
        else: 
            print_help()
            sys.exit()

    if args.org_name is not None:
        if args.org_name != "":
            drawing_mode = "target"
            member_list = ParseOrg(args.url, args.org_name)
            target_AS = ParseTargetLinks(args.url, member_list)
        else:
            print_help()
            sys.exit()

    if args.output_file is not None:
        if args.output_file != "":
            output_file = args.output_file
        else:
            print_help()
            sys.exit()

    if args.file_format is not None:
        if args.file_format != "":
            file_format = args.file_format
        else:
            print_help()
            sys.exit()
    #if drawing mode is still the default
    if drawing_mode == "full": 
        asns = ParseAsns(args.url)
        links = ParseLinks(args.url)

    if selected_key is "customer_cone_asnes":
        key_function = CustomerConeAsnes 

    min_x, min_y, max_x, max_y, max_value = SetUpPosition()
    PrintGraph(min_x, min_y, max_x, max_y, max_value)
###########################\
#method to parse the first page of links
def ParseFirstPage(url):
    global verbose
    global links    
    seen_asns = set()
    new_url = "http://" + url + "/links?populated"

    if verbose:
        print ("loading",new_url)
    links_json = url_load(new_url)
    link_data = links_json["data"]
    links.extend(link_data)

    #aadd asns to list
    for link in links:
        asn0 = str(link["asn0"])
        #ignore duplicates
        if asn0 not in seen_asns:
            seen_asns.add(asn0)
            ParseAsn(url, asn0)
        asn1 = str(link["asn1"])
        if asn1 not in seen_asns:
            seen_asns.add(asn1)
            ParseAsn(url, asn1) 
#method to parse links of target AS
def ParseTargetLinks(url, target_list):
    global verbose
    global links

    seen_asns = set()
    target_AS = set()
    for target in target_list:
        target_AS.add(target)
        #add target asn to as list
        ParseAsn(url, target)
        new_url = "http://" + url + "/asns/" + target + "/links"
        if verbose:
            print ("loading",new_url)
        links_json = url_load(new_url)
        link_data = links_json["data"]
        #assign dictionary values and add asns to support code below
        for link in link_data:
            link["asn0"] = int(target)
            if str(link["asn"]) not in seen_asns:
                seen_asns.add(str(link["asn"]))
                ParseAsn(url, str(link["asn"]))
            link["asn1"] = link["asn"] 
        links.extend(link_data)
    
    return target_AS
#method to parse single link
def ParseSingleLink(url, link_data):
    global verbose    
    global links
    link_list = link_data.split(",")

    if len(link_list) != 2:
        sys.stderr.write("invalid entry")
        sys.exit()
    asn0 = link_list[0]
    asn1 = link_list[1]
    #add AS in link to list 
    ParseAsn(url, asn0)
    ParseAsn(url, asn1) 
    new_url = "http://" + url + "/links/" + asn0 + "/" + asn1

    if verbose:
        print ("loading",new_url)
    links_json = url_load(new_url)
    link_data = links_json["data"]
    #assign dictionary values to support code below
    link_data["asn0"] = int(asn0)
    link_data["asn1"] = int(asn1)    
    links.append(link_data)
#method to parse organization name and get member list to set targets
def ParseOrg(url, org_name):
    global verbose
    global target_AS 
    new_url = "http://" + url + "/orgs/" + org_name
     
    if verbose:
        print ("loading",new_url)
    org_json = url_load(new_url)
    members = org_json["data"]["members"]
    return members     
#method to parse a single asn
def ParseAsn(url, asn): 
    global asns
    new_url = "http://" + url + "/asns/" + asn
    
    asn_json = url_load(new_url)
    asn_data = asn_json["data"] 
    asns.append(asn_data)
#method to populate links array with object data from url
def ParseLinks(url):
    global verbose
    new_url = "http://" + url + "/links"
    if verbose:
        print ("loading",new_url)

    links_json = url_load(new_url)
    link_total = links_json["total"]
    page_count = 1;
    link_data = links_json["data"]
    #loop through until data array is empty
    while(len(link_data) > 0):
        links.extend(link_data)
        page_count += 1
        new_url = "http://" + url + "/links?page=" + str(page_count)
        links_json = url_load(new_url)
        link_data = links_json["data"]
    return links
#method to populate asn array with object data from url
def ParseAsns(url):
    global verbose
    new_url = "http://" + url + "/asns?populate"
    if verbose:
        print ("loading",new_url)
    
    asn_json = url_load(new_url)
    asn_total = asn_json["total"]
    page_count = 1;
    asn_data = asn_json["data"] 
    #loop through until data array is empty  
    while(len(asn_data) > 0):
        asns.extend(asn_data)
        page_count += 1
        new_url = "http://" + url + "/asns?populate&page=" + str(page_count)
        asn_json = url_load(new_url)
        asn_data = asn_json["data"]
    return asns
#method to pull data from online url
def download(url):
    try:
        #print ("downloading",url)
        response = urllib.request.urlopen(url, timeout=5)
        return response.readline()
    except urllib.error.HTTPError as e:
        traceback.print_stack()
        print ('HTTPError = ' + str(e.code))
        sys.exit()
    except Exception:
        traceback.print_stack()
        print ('generic exception: ' + traceback.format_exc())
        sys.exit()
#method to pull data from API
def url_load(url):
    url_data = download(url)
    res_json = url_data.decode('utf-8')
    decoder = json.JSONDecoder()
    res = decoder.decode(res_json)
    if "total" not in res_json and "data" not in res_json:
        sys.stderr.write("failed to download"+url)
        sys.exit()
    return res
'''
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
'''
#method to get the max value when not using full graph
def GetMaxValue():
    url = "http://as-rank.caida.org/api/v1/asns?populate&ranked&count=1"
    max_json = url_load(url)
    max_AS = max_json["data"][0]
    max_value = key_function(max_AS)
    return max_value
def TargetChangeSize():
    for AS in asns:
        AS["size"] = AS["size"] * 1.10
    for target_id in target_AS:
        target = asSearch(int(target_id))
        if target != None:
            target["size"] = MAX_SIZE * 1.10
           
###########################
#method to determine positions of all asn nodes and links based on data
def SetUpPosition():
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
    if verbose:
        print("numNodes:",len(asns))
    while asIndex < len(asns): 
        AS = asns[asIndex]
        value = key_function(AS)
        if "longitude" not in AS or value is None or value <= 0:
            '''
            if focus_asn == int(AS["id"]):
                sys.stderr.write("invalid focus asn")
                sys.exit()
            '''                               
            num_asn_skipped += 1
            #pop last AS from end of list
            temp = asns.pop();
            #if not at the end of the list
            if asIndex < len(asns):
                #replace the asn at current position with last asn
                asns[asIndex] = temp
                continue
        else:	
            #add AS object to dictionary
            asn_dict[int(AS["id"])] = AS
            #move loop forward
            asIndex += 1

    #get max value from url 
    max_value = GetMaxValue()
    print("maxValue:" + str(max_value) + "\n")
    #set min max x y based on max value
    radius = (math.log(max_value+1) - math.log(0+1) +.5)*100
    min_x = radius * math.cos(math.pi)
    max_x = radius * math.cos(0) 
    min_y = radius * math.sin(math.pi * 3/2)    
    max_y = radius * math.sin(math.pi/2)
    
    if verbose:
        print("Assigning coordinates to nodes (num nodes:",len(asns),")")
    #loop through current asn list, calculating and adding coordinates to each asn  
    #focus_x = 0
    #focus_y = 0
    for AS in asns:
        value = key_function(AS)
        angle = -2 * 3.14 * float(AS["longitude"]) / 360
        radius = (math.log(max_value+1) - math.log(value+1) +.5)*100
        size = int((MAX_SIZE-3)* (math.log(value+1)/math.log(max_value+1)) )+3;
        #calculate new x and y using polar coordinate math
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        #add new values to AS object 
        AS["x"] = x
        AS["y"] = y
        AS["size"] = size
        AS["color"] = Value2Color(value/max_value)
        
        #store x and y values outside loop if AS is focus asn
        #if focus_asn == int(AS["id"]):
            #focus_x = AS["x"]
            #focus_y = AS["y"]
    '''
    for AS in asns:
        x = AS["x"]
        y = AS["y"]
        size = AS["size"]
        #if using fisheye effect
        if focus_asn > -1:
            size = AS["size"]
            old_x0 = x
            old_x1 = x + size
            new_coords = FishEye(x, y, focus_x, focus_y)
            AS["x"]  = x = new_coords[0]
            AS["y"]  = y = new_coords[1]
    '''
    #increase min max x y slightly, move all ASNes to adjust 
    min_x += min_x*.05
    min_y += min_y*.05
    for AS in asns:
        AS["x"] -= min_x
        AS["y"] -= min_y  
    max_x -= min_x
    max_y -= min_y
    min_x = min_y = 0
    
    if len(target_AS) != 0:
        TargetChangeSize()

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
            value = key_function(AS)
            if selected_key not in link:
                link[selected_key] = value
            elif value < link[selected_key]:
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
        #link["distance"] = math.sqrt(math.pow(link["x2"] - link["x1"], 2) + math.pow(link["y2"] - link["y1"], 2)) 
        #calculate color
        value = link[selected_key]
        link["color"] = Value2Color(value/max_value)

        if len(target_AS) != 0:
            link["width"] = 2
        else:
            link["width"] = 0.5

        linkIndex += 1
    

   
    print ("numNodes:", len(asns),"numSkipped:",num_asn_skipped)
    print ("numLinks:", len(links),"numSkipped:",num_links_skipped) 
    return min_x, min_y, max_x, max_y, max_value

#helper function to get the customer cone asns of an AS
def CustomerConeAsnes(AS):
    if "cone" not in AS or "asns" not in AS["cone"]:
        return None
    else:
        return AS["cone"]["asns"]
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
#helper function to apply fisheye effect to a pair of xy coordinates 
def FishEye(x, y, focus_x, focus_y):
    #calculate distance and angle from focus point 
    angle = math.atan2(y - focus_y, x - focus_x) 
    r = math.sqrt(math.pow(x-focus_x, 2) + math.pow(y - focus_y, 2))
    #focal length of the "lens"  
    f = 300
    #angle from optical axis
    theta = math.atan2(r,f)
    #calculate new distance from focus point
    new_r = math.tan(theta/2) * 2 * f
    #new_r = theta * f    
    #new_r = 2 * f * math.sin(theta/2)
    #new_r = f * math.sin(theta)    
    new_x = focus_x + (new_r * math.cos(angle))
    new_y = focus_y + (new_r * math.sin(angle)) 
    return (new_x, new_y)
    
#method to print the visualization onto an image
def PrintGraph(min_x, min_y, new_max_x, new_max_y, max_value):  
    global asns
    global links
    #sort nodes and links lists
    asns = sorted(asns, key = key_function)
    links = sorted(links, key = lambda link: link[selected_key])    
    # Make calls to PyCairo
    #set up drawing area
    scale = 0.6
    max_x = new_max_x * scale
    max_y = new_max_y * scale
    WIDTH = int(new_max_x) 
    HEIGHT = int(new_max_y * 0.8) 
    
    if file_format == "PDF":
        print("using pdf")
        surface = cairo.PDFSurface(output_file, WIDTH, HEIGHT)
    if file_format == "SVG":
        print("using svg") 
        surface = cairo.SVGSurface(output_file, WIDTH, HEIGHT)
    if file_format == "PNG":
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT) 
    cr = cairo.Context(surface)
	
    PrintHeader(cr, min_x,min_y,max_x,max_y)
    if print_key:
        PrintKey(cr, new_max_x, new_max_y, max_value, scale)
    cr.translate((WIDTH - max_x) / 2, (HEIGHT - max_y) / 2) 
    PrintLinks(cr, max_value, scale)
    PrintNodes(cr, scale)
    PrintNames(cr, scale)

	# We do not need suppport for this now
	#if (defined $name_file) {
	#    PrintNames(@nodes);
	#}
	##if (defined $print_key) {
	#$max_x = PrintKey($max_x,$max_y, $max_value);
	#}
	#PrintEnder();
    if file_format == "PNG":
        surface.write_to_png(output_file) 
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
        width = link["width"]
        linkInfo = ("links", x1, y1, x2, y2, color)
        #skip if is duplicate
        if linkInfo not in seen:
            seen.add(linkInfo)			
            #draw line
            cr.move_to(x1,y1)
            cr.line_to(x2, y2)
            cr.set_source_rgb(color[0], color[1], color[2])
            cr.set_line_width(link["width"])
            cr.stroke()			
    return
#helper method for printGraph to print the nodes onto the image
def PrintNodes(cr, scale):
    seen = set()
    #focus_asn_node = None
    for AS in asns:
        #if int(AS["id"]) == focus_asn:
            #focus_asn_node = AS
            #continue
        #calculate coordinates and get colors
        x = AS["x"] * scale 
        y = AS["y"] * scale
        #decrease size so that dots arent too big 
        size = AS["size"] * scale
        color = AS["color"]
        nodeInfo = ("nodes", size, x, y, color)
        #skip if is duplicate
        if nodeInfo not in seen:
            PrintNode(cr, AS, scale)
    #if focus_asn_node is not None:
        #PrintNode(cr, focus_asn_node, scale)
    return
def PrintNode(cr, AS, scale):
    #calculate coordinates and get colors
    x = AS["x"] * scale 
    y = AS["y"] * scale
    #decrease size so that dots arent too big 
    size = AS["size"] * scale
    color = AS["color"]
    #save current context with no path
    cr.save()
    #plot point
    cr.rectangle(x, y, size, size)
    #fill with color 
    cr.set_source_rgb(color[0], color[1], color[2])
    cr.fill_preserve()
    #outline	
    cr.set_source_rgb(0, 0, 0)
    cr.set_line_width(1)
    cr.stroke()
    #restore to saved context to wipe path
    cr.restore()
#helper method for printing out names of AS
def PrintNames(cr, scale):
    node_info = []
    for AS in asns:
        size = AS["size"] * scale
        x0 = AS["x"] * scale
        y0 = AS["y"] * scale
        x1 = x0 + size 
        y1 = y0 + size
        node_info.append({"x0" : x0, "y0" : y0, "x1" : x1, "y1" : y1})
    name_info_list = []
    reverse_asns = list(reversed(asns))
    for AS in reverse_asns:
        if "name" not in AS["org"]:
            continue
        else:
            name = AS["org"]["name"] 
            names = name.split()
            if len(names) > 1:
                name = names[0] + " " + names[1]
            value = key_function(AS)
            if value < name_filter:
                continue
            #next if (defined $name_filter && $value < $name_filter)
            size = AS["size"]
            font_size = "%.1f" % (17 * size / MAX_SIZE)
            stroke_size = "%.1f" % (0.5 * size / MAX_SIZE + 2)

            name = re.sub(r'Communication.*', '', name)
            name = re.sub(r'-.*', '', name)
            name = re.sub(r',.*', '', name)
            name = re.sub(r'\&', '&amp', name)
            name = re.sub(r'.+de Redes Colomsat S.A', 'Administracin de', name)
            
            name = AS["id"] + " (" + name + ") "
            center_x = (AS["x"] + AS["size"] / 2) * scale
            center_y = (AS["y"] + AS["size"] / 2) * scale
            color = AS["color"]
            
            width = 0
            for char in name:
                if char.isupper():
                    width = width + (0.5 * float(font_size))
                else:
                    width = width + (0.4 * float(font_size))

            height = 0.8 * float(font_size)
                 
            theta = 0
            name_info = {}
            #overlap

            size = size * 0.75 * scale
            while (theta < 2 * math.pi):
                x = center_x + size * math.cos(theta)
                y = center_y + size * math.sin(theta) 
                x0 = x
                y0 = y
                x1 = x + width
                y1 = y + height
                if x < center_x: 
                    x0 = x - width
                    x1 = x;
                name_info = { "x" : x, "y" : y, "x0" : x0, "y0" : y0, "x1" : x1, "y1" : y1, "name" : name,}
                overlap = None
                for i in (name_info_list, node_info):    
                    for info in i:
                        if Overlap(info, name_info):
                            overlap =1
                            break

                if overlap == None:
                    break
                theta = theta + .1*math.pi;

            if overlap is None:
                x = name_info["x"]
                y = name_info["y"]
                cr.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, 
                    cairo.FONT_WEIGHT_NORMAL)
                cr.set_font_size(float(font_size))

                cr.save()
                cr.move_to(x, y)
                name = name_info["name"]
                cr.text_path(name)
                cr.set_source_rgb(1, 1, 1)
                cr.set_line_width(float(stroke_size))
                cr.stroke_preserve()
                cr.set_source_rgb(0, 0, 0)
                cr.fill()
                cr.restore()

            name_info_list.append(name_info)

def Overlap(a, b):
    return (a["x0"] <= b["x0"] and b["x0"] <= a["x1"] or a["x0"] <= b["x1"] and b["x1"] <= a["x1"] or b["x0"] <= a["x0"] and a["x0"] <= b["x1"]) and (a["y0"] <= b["y0"] and b["y0"] <= a["y1"] or a["y0"] <= b["y1"] and b["y1"] <= a["y1"] or b["y0"] <= a["y0"] and a["y0"] <= b["y1"])
#helper method for printGraph to print the color key onto the image
def PrintKey(cr, new_max_x, new_max_y, new_max_value, scale):
    max_x = new_max_x * 0.95
    max_y = new_max_y * 0.8
    max_value = new_max_value

    key_width = max_x / 45 
    key_x_margin = key_width * 0.2
    key_x = max_x - key_width - key_x_margin 

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
    #cr.rectangle(key_x, key_y, key_width, key_height)
    #cr.set_line_width(5)
    #cr.set_source_rgb(0,0,0)
    #cr.stroke()
    
    cr.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, 
    cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(key_width / 2)
    cr.set_source_rgb(0, 0, 0)
    for value in range(11):
        fraction = value / 10
        number = ("%d" % (max_value * fraction))
        x1 = key_x 
        y1 = (key_y + key_height * (1 - fraction))

        x2 = key_x + key_width        
        y2 = y1

		
        cr.move_to(x1,y1)
        cr.line_to(x2, y2)
        cr.set_source_rgb(0, 0, 0)
        cr.set_line_width(2)
        cr.stroke()
        cr.move_to(x2 + 10, y2)
        cr.show_text(number)
#run the main method
main(sys.argv[1:])
