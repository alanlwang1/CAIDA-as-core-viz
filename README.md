
## AS Core python code 


Original goal was to port scripts-old/make_svg_graph.pl to python  
The script produces a graph that looks like this. 

    http://www.caida.org/research/topology/as_core_network/pics/2017/ascore-2017-feb-ipv4-poster-2048x1518.png


Code modified from first loading data from the current set of files, then to working with the jsonl files in data,  
and finally to working with CAIDA's RESTful API at as-rank.caida.org/api/v1  

Code also modified to use customer cone size instead of transit degree to calculate distance of nodes from center of visualization. 

With json files, the code runs as follows: 

    ./as-core-graph.py -l data/links.jsonl -a data/asns.jsonl

With the API, the code runs as follows: 

    ./as-core-graph.py -u as-rank.caida.org/api/v1
