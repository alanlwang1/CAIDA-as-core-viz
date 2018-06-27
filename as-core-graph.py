#!  /usr/bin/env python3
import argparse
import sys

verbose = False
asns = []
links = []

def print_help():
    print (sys.argv[0],"-l links.jsonl -a asns.jsonl")

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

def ParseLinks(fname):
    global verbose
    global asns
    global links
    if verbose:
        print ("loading",fname)

def ParseAsns(fname):
    global verbose
    global asns
    if verbose:
        print ("loading",fname)

###########################

def SetUpPosition():
    min_x = 0
    min_y = 0
    max_x = 0
    max_y = 0
    max_value = 0
    return min_x, min_y, max_x, max_y, max_value

def PrintGraph(min_x, min_y, max_x, max_y, max_value):
    # Make calls to PyCairo
    PrintHeader(min_x,min_y,max_x,max_y);
    PrintLinks(max_value);
    PrintNodes();

    # We do not need suppport for this now
    #if (defined $name_file) {
    #    PrintNames(@nodes);
    #}
    ##if (defined $print_key) {
        #$max_x = PrintKey($max_x,$max_y, $max_value);
    #}
    #PrintEnder();

def PrintHeader(min_x,min_y,max_x,max_y):
    return

def PrintLinks(max_value):
    return

def PrintNodes():
    return

main(sys.argv[1:])
