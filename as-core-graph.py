#!  /usr/bin/env python3
import re
import traceback
import argparse
import sys
import math
import json
import cairo
import urllib.request
import urllib.parse
import urllib.error

#boolean controlling whether to print messages about run status
verbose = False
#boolean controlling grayscale of image printed
grayscale = False
#boolean controlling whether to print color key on image
print_key = False
#boolean controlling whether to print continent halo on image
print_continents = False
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
#width of margin around image
outer_margin = 10
inner_margin = 10
#pixel size of image
image_size = -1 

#method to print how to run script
def print_help():
    print (sys.argv[0],"-u as-rank.caida.org/api/v1")
#main method
def main(argv):
    global verbose
    global print_key
    global print_continents
    global key_function
    global focus_asn
    global drawing_mode
    global links
    global asns
    global target_AS
    global output_file
    global file_format
    global outer_margin
    global inner_margin
    global image_size

    parser = argparse.ArgumentParser()
    #parser.add_argument("-l", type=str, dest="links", help="loads in the asn links file")
    #parser.add_argument("-a", type=str, dest="asns", help="loads in the asn links file")   
    #parser.add_argument("-f", type=int, nargs='?', const=-1, dest="focus", help="number of AS to focus on using fisheye effect")
    parser.add_argument("-u", type=str, dest="url", help="loads in the API url")
    parser.add_argument("-k", dest="print_key", help="prints out color key for visualization", action="store_true")
    parser.add_argument("-v", dest="verbose", help="prints out lots of messages", action="store_true")
    parser.add_argument("-c", dest="print_continents", help="prints out continent halo for visualization", action="store_true")
    parser.add_argument("-F", default=None, dest="first_page", help="draw only the first page of links", action="store_true")
    parser.add_argument("-a", type=str, default=None, nargs='?', const="", dest="target", help="asns to display neighbors of, separated by comma") 
    parser.add_argument("-l", type=str, default=None, nargs='?', const="", dest="link_asns", help="ASnes of a single link, separated by colon")
    parser.add_argument("-O", type=str, default=None, nargs='?', const="", dest="org_name", help="Organization name of members to focus on")
    parser.add_argument("-o", type=str, default=None, nargs='?', const="", dest="output_file", help="Name of output file to write graph to")
    parser.add_argument("-f", type=str, default="PNG", nargs='?', const="", dest="file_format", choices=["SVG","PDF","PNG"], help="file format of output file to write graph to")
    parser.add_argument("-s", type=int, default=None, nargs='?', const=-1, dest="image_size", help="Pixel size of output image")
    args = parser.parse_args()

    url = None
    if args.url is None:
        print_help()
        sys.exit()
    else:
        url = args.url
        if not re.search("^http",url):
            url = "http://"+url

    if args.print_key:
        print_key = True

    if args.verbose:
        verbose = True
    
    if args.print_continents:
        inner_margin = 110
        print_continents = True

    if args.first_page is not None:
        if args.first_page:
            if drawing_mode == "full":
                drawing_mode = "first_page"
                ParseFirstPage(url)
   
    if args.target is not None:
        if args.target != "":
            if drawing_mode == "full": 
                drawing_mode = "target"     
                target_list = args.target.split(",")
                target_AS = ParseTargetLinks(url, target_list)
        else: 
            print_help()
            sys.exit()

    if args.link_asns is not None:
        if args.link_asns != "":  
            if drawing_mode == "full":
                drawing_mode = "single_link" 
                ParseSingleLink(url, args.link_asns)
        else: 
            print_help()
            sys.exit()

    if args.org_name is not None:
        if args.org_name != "":
            drawing_mode = "target"
            target_AS = ParseOrgMembers(url, args.org_name)
            ParseOrgLinks(url, args.org_name)
        else:
            print_help()
            sys.exit()

    if args.output_file is not None:
        if args.output_file != "":
            if args.output_file == "-":
                output_file = sys.stdout.buffer
            else:
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

    if args.image_size is not None:
        if args.image_size > -1:
            image_size = args.image_size
        else:
            print_help()
            sys.exit()
            
    #if drawing mode is still the default
    if drawing_mode == "full": 
        asns = ParseAsns(url)
        links = ParseLinks(url)

    if selected_key is "customer_cone_asnes":
        key_function = CustomerConeAsnes 

    min_x, min_y, max_x, max_y, max_value = SetUpPosition(url)
    PrintGraph(min_x, min_y, max_x, max_y, max_value)


######################################################################
## Download and Parse methods
######################################################################

#method to parse the first page of links
def ParseFirstPage(url):
    global verbose
    global links    
    seen_asns = set()
    new_url = url + "/links?populated"

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
        new_url = url + "/asns/" + target + "/links"
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
    link_list = link_data.split(":")

    if len(link_list) != 2:
        sys.stderr.write("invalid entry")
        sys.exit()
    asn0 = link_list[0]
    asn1 = link_list[1]
    #add AS in link to list 
    ParseAsn(url, asn0)
    ParseAsn(url, asn1) 
    new_url = url + "/links/" + asn0 + "/" + asn1

    if verbose:
        print ("loading",new_url)
    links_json = url_load(new_url)
    link_data = links_json["data"]
    if link_data == None:
        sys.stderr.write("invalid entry")
    #assign dictionary values to support code below
    link_data["asn0"] = int(asn0)
    link_data["asn1"] = int(asn1)    
    links.append(link_data)

#method to parse organization name and get member list to set targets
def ParseOrgMembers(url, org_name):
    global verbose
    url += "/orgs/" + org_name+ "/members"
     
    if verbose:
        print ("loading",url)

    asns = set()
    for asn in download_paged_data(url):
        asns.add(asn)
    return asns

#method to parse organization links - will need to update later when api changes
def ParseOrgLinks(url, org_name):
    global verbose 
    global asns
    global links
    links = []

    url = url + "/orgs/" + org_name+ "/neighbors?populate"
    if verbose:
        print ("loading",url)
    seen_asn = set()
    for org_links in download_paged_data(url):
        for link in org_links["links"]:
            links.append({
                    "relationship":link["relationship"],
                    "asn0":int(link["asn0"]["id"]),
                    "asn1":int(link["asn1"]["id"]),
                })
            for asn_info in [link["asn0"],link["asn1"]]:
                asn = asn_info["id"]
                if asn not in seen_asn:
                    asns.append(asn_info)
                    seen_asn.add(asn)

#method to parse a single asn
def ParseAsn(url, asn): 
    global asns
    url += "/asns/" + asn
    
    asn_json = url_load(url)
    asn_data = asn_json["data"] 
    asns.append(asn_data)

#method to populate links array with object data from url
def ParseLinks(url):
    global verbose
    url = url + "/links"
    if verbose:
        print ("loading",url)
    return download_paged_data(url)

#method to populate asn array with object data from url
def ParseAsns(url):
    global verbose
    url = url + "/asns?populate&ranked"
    if verbose:
        print ("loading",url)
    return download_paged_data(url)

#method to pull data from online url
def download(url):
    try:
        #print ("downloading",url)
        response = urllib.request.urlopen(url, timeout=5)
        return response.readline()
    except urllib.error.HTTPError as e:
        #traceback.print_stack()
        print ('error for url:',url);
        print ('HTTPError = ' + str(e.code))
        sys.exit()
    except Exception as e:
        #traceback.print_stack()
        #print ('generic exception: ' + traceback.format_exc())
        print ('error for url:',url);
        print ('generic exeception:',e)
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

def download_paged_data(url):
    global verbose
    if not re.search("\?",url):
        url += "?";
    else:
        url += "&";
    objects = []
    page_count = 1
    while True:
        new_url =  url + "&page=" + str(page_count)
        data = url_load(new_url)
        if len(data["data"]) < 1:
            return objects
        objects.extend(data["data"])
        page_count += 1


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

######################################################################
## Other Helper methods
######################################################################

#method to get the max value when not using full graph
def GetMaxValue(url):
    url = url+"/asns?populate&ranked&count=1"
    max_json = url_load(url)
    max_AS = max_json["data"][0]
    max_value = key_function(max_AS)
    return max_value

#method to change sizes to make target AS more noticable
def TargetChangeSize():
    for AS in asns:
        AS["size"] = AS["size"] * 1.10

    for target_id in target_AS:
        target = asSearch(int(target_id))
        if target != None:
            target["size"] = MAX_SIZE * 1.10
            target["color"] = (1, 1, 1)

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

######################################################################
## Methods to assign positions and colors
######################################################################
#method to determine positions of all asn nodes and links based on data
def SetUpPosition(url):
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
    max_value = GetMaxValue(url)
    print("maxValue:" + str(max_value) + "\n")

    #set min max x y based on max value
    radius = (math.log(max_value+1) - math.log(1+1) +.5)*100
    min_x = radius * math.cos(math.pi)
    max_x = radius * math.cos(0) 
    min_y = radius * math.sin(math.pi * 3/2)    
    max_y = radius * math.sin(math.pi/2)
    
    if verbose:
        print("Assigning coordinates to nodes (num nodes:",len(asns),")")

    #loop through current asn list, calculating and adding coordinates to each asn  
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
        
    #increase min max x y slightly, move all ASNes to adjust 
    min_x += min_x*.05
    min_y += min_y*.05

    for AS in asns:
        AS["x"] -= min_x
        AS["y"] -= min_y  

    max_x -= min_x
    max_y -= min_y
    min_x = min_y = 0
    
    #if targets exist, change sizes
    if len(target_AS) != 0:
        TargetChangeSize()

	#links
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
		
        #get information to draw line
        size1 = as1["size"]
        size2 = as2["size"]
        #center xy coordinates on the nodes
        link["x1"] = as1["x"]+ (size1 / 2)
        link["y1"] = as1["y"]+ (size1 / 2)
        link["x2"] = as2["x"]+ (size2 / 2)
        link["y2"] = as2["y"]+ (size2 / 2) 

        #calculate color
        value = link[selected_key]
        link["color"] = Value2Color(value/max_value)

        #change link width if target
        if len(target_AS) != 0:
            link["width"] = 2
        else:
            link["width"] = 0.5

        linkIndex += 1
     
    print ("numNodes:", len(asns),"numSkipped:",num_asn_skipped)
    print ("numLinks:", len(links),"numSkipped:",num_links_skipped) 
    return min_x, min_y, max_x, max_y, max_value

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

######################################################################
## Print methods
######################################################################

#method to print the visualization onto an image
def PrintGraph(min_x, min_y, max_x, max_y, max_value):  
    global asns
    global links
    global image_size

    #sort nodes and links lists
    asns = sorted(asns, key = key_function)
    links = sorted(links, key = lambda link: link[selected_key])  
  
    # Make calls to PyCairo
    #set up drawing area
    if image_size > -1:
        WIDTH = image_size
        HEIGHT = image_size 
    else:
        image_size = max_x
        WIDTH = int(max_x) + inner_margin
        HEIGHT = int(max_y) + inner_margin

    #set up file format
    if file_format == "PDF":
        print("using pdf")
        surface = cairo.PDFSurface(output_file, WIDTH, HEIGHT)
    if file_format == "SVG":
        print("using svg") 
        surface = cairo.SVGSurface(output_file, WIDTH, HEIGHT)
    if file_format == "PNG":
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT) 
    cr = cairo.Context(surface)

    cr.translate(outer_margin - 15, outer_margin - 15)
    cr.scale((image_size - inner_margin)/max_x, (image_size - inner_margin)/max_y)

    #print everything
    PrintHeader(cr, min_x,min_y,max_x,max_y)
    if print_key:   
        cr.translate(outer_margin, outer_margin + HEIGHT / 10)
        PrintKey(cr, WIDTH, HEIGHT, max_x, max_y, max_value)
        cr.scale(0.8, 0.8)
    if print_continents:
        PrintContinents(cr, WIDTH, HEIGHT, max_x, max_y, max_value)
        cr.translate(inner_margin - 25, inner_margin - 25)

    PrintLinks(cr, max_value)
    PrintNodes(cr)

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
def PrintLinks(cr, max_value):
    seen = set()
    for link in links:
        x1 = link["x1"] 
        y1 = link["y1"] 
        x2 = link["x2"] 
        y2 = link["y2"] 
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
def PrintNodes(cr):
    seen = set()
    #focus_asn_node = None
    for AS in asns:
        #calculate coordinates and get colors
        x = AS["x"]  
        y = AS["y"] 
        #decrease size so that dots arent too big 
        size = AS["size"] 
        color = AS["color"]
        nodeInfo = ("nodes", size, x, y, color)
        #skip if is duplicate
        if nodeInfo not in seen:
            PrintNode(cr, AS)
    return

def PrintNode(cr, AS):
    #calculate coordinates and get colors
    x = AS["x"]
    y = AS["y"]
    #decrease size so that dots arent too big 
    size = AS["size"]
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
    return

#helper method for printGraph to print the continent halo onto the image
def PrintContinents(cr, WIDTH, HEIGHT, max_x, max_y, max_value):
    continents =  [
        {
            "name" : "North America",
            "lon_start" : -168.3359374,
            "lon_end"  : -56.8596442,
            "order" : 0,
            "color" : [255, 192, 203] #pink
        },
        {
            "name" : "South America",
            "lon_start" : -83.710541,
            "lon_end"  : -36.601166,
            "order" : 1,
            "color" : [144, 238, 144] #light green
        },
        {
            "name" : "Europe",
            "lon_start" : -9.882416,
            "lon_end"  : 33.711334,
            "order" : 0,
            "color" : [173, 216, 230] #light blue
        },
        {
            "name" : "Africa",
            "lon_start" : -16.3863222,
            "lon_end"  : 51.3773497,
            "order" : 1,
            "color" : [240, 128, 128] #light coral
        },
        {
            "name" : "Asia",
            "lon_start"  : 33.711334,
            "lon_end"  : 190,
            "order" : 0,
            "color" : [220, 220, 220] #gainsboro
        },
        {
            "name" : "Oceania",
            "lon_start" : 94.2728129,
            "lon_end"  : 180,
            "order" : 1,
            "color" : [255, 228, 181] #moccassin
        }
        ]
        
    x_center = max_x / 2 + inner_margin
    y_center = max_y / 2 + inner_margin 
    #radius = RADIUS
    radius = max_x / 2 + 20
    width = 40

    for continent in continents:
        name = continent["name"]
        mid_lon = (continent["lon_start"] + continent["lon_end"]) / 2
        lon = (continent["lon_start"], continent["lon_end"])
        color = continent["color"] 
        #convert to float
        index = 0
        while index < len(color): 
            v = color[index]
            color[index] = float(v / 255)
            index += 1
        shift = max_value * 1.1 * continent["order"]

        font_size = "%.1f" % (2 * MAX_SIZE)
        
        x = []
        y = []
        angle_list = []
        r = radius + continent["order"] * (60)
        for i in range(2):
            angle = -2 * math.pi * (lon[i] / 360)
            angle_list.append(angle)
            x.append(x_center + r * math.cos(angle))
            y.append(y_center + r * math.sin(angle))

        r_name = r - radius * 0.015
        name_center = (lon[1] + lon[0]) / 2
        name_angle = -2 * math.pi * (name_center/360)
        rotate = math.pi / 2 - (math.pi * name_center / 180)
        while rotate < 0:
             rotate = rotate + 2 * math.pi
        
        x_name = x_center + r_name * math.cos(name_angle)
        y_name = y_center + r_name * math.sin(name_angle)
   
        
        cr.move_to(x[0], y[0])
        cr.arc_negative(x_center, y_center, r, angle_list[0], angle_list[1])
        cr.set_line_width(width)
        cr.set_source_rgb(color[0], color[1], color[2])
        cr.stroke()
            
        cr.select_font_face("Arial" , cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(float(font_size))
        fascent, fdescent, fheight, fxadvance, fyadvance = cr.font_extents()
        x_off, y_off, tw, th = cr.text_extents(name)[:4]
        nx = -tw/2.0
        ny = fheight/2 - 20

        cr.save()
        cr.translate(x_name, y_name)
        cr.rotate(rotate)
        cr.translate(nx, ny)
        cr.move_to(0, 0)
        cr.set_source_rgb(0, 0, 0)
        cr.show_text(name)
        cr.restore()
    return

#helper method for printGraph to print the color key onto the image
def PrintKey(cr, WIDTH, HEIGHT, new_max_x, new_max_y, new_max_value):
    max_x = new_max_x * 0.95
    max_y = new_max_y * 0.8
    max_value = new_max_value

    key_width = max_x / 45 
    key_x_margin = key_width * 0.2
    key_x = (WIDTH * max_x / (image_size - inner_margin)) - key_width - key_x_margin

    key_height = 8 * max_y / 10 
    key_y = ((HEIGHT * max_y / (image_size - inner_margin)) - key_height) / 2
	
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
        cr.move_to(x2 + 15, y2)
        cr.show_text(number)
    return

#run the main method
main(sys.argv[1:])
