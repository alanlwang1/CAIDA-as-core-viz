
## AS Core python code 

#### Port the current perl code to python

- Original location of code was cvs:WIP/viz/as-core/bin/make_svg_graph.pl

The goal is to port scripts-old/make_svg_graph.pl to python. It will be producing 
a graph that looks like this:

    http://www.caida.org/research/topology/as_core_network/pics/2017/ascore-2017-feb-ipv4-poster-2048x1518.png

The main function you will be porting is PrintGraph (line 160)
and it's subfunctions.

You will be replacing the code that loads data from the current
set of files to work with the jsonl files in you will find in data.

Keep in mind that you at some point the code is going to need 
be able to work against as-rank.caida.org/api/v1. So you should write
your code to work against the original.

It should be run as follows on the command line:

    ./as-core-graph.py -l data/links.jsonl -a data/asns.jsonl

We will be switching from transit degree to customer cone for the distance 
from the center.

#### Working with as-rank.caida.org/api/v1

- Once you have the code working with the static files. It's time to 
  get it to work with the API.

    ./as-core-graph.py -u as-rank.caida.org/api/v1
