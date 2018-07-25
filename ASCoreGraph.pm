#!/usr/bin/env perl
#
#   This creates 
#	INPUT:
#	    links file - a listing of all the links with each
#		line in the file being a link.
#		    asn0 to wieght
#			asn0 - the source of the link
#			to - the end of the link
#			wieght - the wieght of the link
#	    loc file - a list of all the information about the as
#		used in the link file.  With a single as on each line.
#		    as, name, city, state, country, continent, lat,
#		      long, source type, source information
#		    as - the as's basic name
#		    city - city the as is located at
#		    state - state the as is located at
#		    country - country the as is located at
#		    continent - continent the as is located at
#		    lat - latitude the as is located at
#		    long - longitude the as is located at
#		    source type- What is the source of this information
#		    source info- Any information used by the source type
#
#	OUTPUT:
#	    Otter data file
#
#
package ASCoreGraph;
use strict;
use warnings;
require Exporter;
our @ISA = qw(Exporter);
my @EXPORT = qw(
    SELECTED
    CUSTOMER
    PEER
    PROVIDER
    );

use CGI;
use Math::Trig;
use strict;


use IPC::Open2;

use constant MAX_SIZE => 7;
use constant WIDTH => 700;
use constant MARGIN_LEFT => 130;
use constant MARGIN_RIGHT => 60;
use constant RADIUS => (WIDTH - MARGIN_LEFT - MARGIN_RIGHT)/2;
use constant HEIGHT => 2*(RADIUS + MARGIN_RIGHT);
#use constant HEIGHT => 500;

use constant ID_AS => 0;
use constant ID_ORG => 1;

use constant CUSTOMER => -1;
use constant PEER => 0;
use constant PROVIDER => 1;
use constant SIBLING => 2;
use constant SELECTED => 3;

my %type_color = %{{
    SELECTED."" => "#FFFFFF",
    PROVIDER."" => "#ED2F3D",
    PEER."" => "#009900",
    CUSTOMER."" => "#6BCAF2",
    SIBLING."" => "#000000",
    }};
my %type_color_node;
foreach my $type (keys %type_color) {
    $type_color_node{$type} = $type_color{$type};
}
$type_color_node{PEER.""} = "rgb(0,240,0)";

my %type_name = %{{
    SELECTED."" => "SELECTED",
    PROVIDER."" => "PROVIDER",
    PEER."" => "PEER",
    CUSTOMER."" => "CUSTOMER",
    SIBLING."" => "SIBLING"
    }};
my %name_type;
foreach my $type (keys %type_name) {
    my $name = $type_name{$type};
    $name_type{$name} = $type;
}

#use FindBin qw($Bin);
#use lib "$Bin/../offline/models";
#use AS;
#use Org;
#my $as_core = new ASCoreGraph();
#$as_core->SetDisplayType(PROVIDER);
##$as_core->SetDisplaySibling();
#$as_core->PrintImageOrg("LVLT-ARIN");
#$as_core->SetWidth(700);
#$as_core->PrintGraphAS(195);
#$as_core->PrintImageAS(195);
#$as_core->PrintGraphOrg(2012);

sub new {
    my ($this) = @_;
    my $class = ref($this) || $this;
    my $self = {
	"asn2nodes" => {},
	"links" => [],
	"sort_type" => "number_asnes",
	"errors" => [],
	"handle" => \*STDOUT
	};
    bless $self, $class;
	
    return $self;
}

sub SetHtmlCache {
    my ($this, $htmlcache) = @_;
    $this->{htmlcache} = $htmlcache;
}

sub SetDisplayTypeName {
    my ($this, $name) = @_;
    my $type = $name_type{$name};
    unless (defined $type) {
	$this->Error("Undefined type:$name");
	$this->PrintErrors();
	return;
    } 
    $this->SetDisplayType($type);
}
sub SetDisplayType {
    my ($this, $type) = @_;
    unless (defined $type_name{$type}) {
	$this->Error("Undefined type:$type");
	$this->PrintErrors();
	return;
    } 
    $this->{type_display} = $type;
    return 1;
}

sub SetDisplaySibling {
    my ($this) = @_;
    $this->{sibling_display} = 1;
}

sub SetURL {
    my ($this, $url) = @_;
    $this->{url} = $url;
}

sub SetWidth {
    my ($this, $width) = @_;
    $this->{target_width} = $width;
}

######################################################
# Loads Functions
######################################################

=cut
sub LoadLoc {
    my ($this) = @_;
    
    my @as_geo = AS->getGeo();
    foreach my $as_geo (@as_geo) {
	my $asn = $as_geo->{asn};
	$this->{asn2nodes}{$asn}{asn} = $asn;
	$this->{asn2nodes}{$asn}{latitude} = $as_geo->{latitude};
	$this->{asn2nodes}{$asn}{longitude} = $as_geo->{longitude};
    }
}


sub LoadLinks {
    my ($this) = @_;
    my $asn2nodes = $this->{asn2nodes};

    my @links = AS->getLinks();
    foreach my $link (@links) {
	my $node0 = $this->{asn2nodes}{$link->{asn0}};
	my $node1 = $this->{asn2nodes}{$link->{asn1}};
	next unless (defined $node0 && defined $node1);
	my $type = $link->{type};
	push @{$this->{links}}, {
	    "node0" => $node0,
	    "node1" => $node1,
	    "type" => $type
	    };
    }
}

sub LoadValues {
    my ($this)= @_;
    my @cones = AS->getCustomerCones();
    foreach my $cone (@cones) {
	my $asn = $cone->{asn};
	$this->{asn2nodes}{$asn}{asn} = $asn;
	foreach my $key (keys %$cone) {
	    if ($key ne "asn") {
		$this->{asn2nodes}{$asn}{$key} = $cone->{$key};
	    }
	}
    }
}
=cut

######################################################
# Print Functions
######################################################
sub PrintImageAS {
    my ($this, $asn) = @_;
    $this->PrintImage($asn, ID_AS);
}
sub PrintGraphAS {
    my ($this, $asn) = @_;
    return $this->PrintGraph($asn, ID_AS);
}

sub PrintImageOrg {
    my ($this, $org) = @_;
    $this->PrintImage($org, ID_ORG);
}
sub PrintGraphOrg {
    my ($this, $org) = @_;
    return $this->PrintGraph($org, ID_ORG);
}

#######################
sub PrintImage {
    my ($this, $id, $id_type) = @_;
    $this->{pixel} = 1;
    my $htmlcache = $this->{htmlcache};

    my $target_width = $this->{target_width};
    my $resize = "";
    if (defined $target_width)  {
	$resize = "-resize ".$target_width."x";
    }
    my $pid = open2(*Reader, *Writer, "/usr/bin/env convert svg:- $resize png:-"); 
    $this->{handle} = \*Writer;
    $this->PrintGraph($id, $id_type);
    close Writer;
    $this->{handle} = \*STDOUT;

    binmode Reader;
    my $buffer;
    my $cgi = new CGI;
    if (defined $htmlcache) {
	$htmlcache->printAndStore($cgi->header(-type=>'image/png'));
    }
    while (read(Reader, $buffer, 20, 0)) {
	if (defined $htmlcache) {
	    $htmlcache->printAndStore($buffer);
	} else {
	    print $buffer;
	}
    }
    close Reader;
}
    

sub PrintGraph {
    my ($this, $id, $id_type) = @_;
    my $htmlcache = $this->{htmlcache};
    my $buffer;
    #if (!defined $this->{pixel} && defined $htmlcache) {
	$buffer = q{};
	open my $handle, ">", \$buffer;
	$this->{handle} = $handle;
    #}
    my ($min_x, $min_y, $max_x, $max_y, $max_value, $nodes, $links)
	= $this->SetUp($id, $id_type);

    my @errors = @{$this->{errors}};
    if ($#errors >= 0) {
	$this->PrintErrors();
    } elsif (!defined $min_x) {
	$this->Error("Unknown error occured");
	$this->PrintErrors();
    } else {
	$this->PrintHeader($min_x, $min_y, $max_x, $max_y, $id);
	if (!defined $this->{pixel}) {
	    $this->PrintToolTip();
	}
	$this->PrintLinks($links);
	if (defined $id) {
	    $this->PrintCenter($min_x, $min_y, $max_x, $max_y);
	}
	$this->PrintNodes($nodes);
	$this->PrintNames($min_x, $min_y, $max_x,$max_y, $nodes);
	$this->PrintContinents($min_x, $min_y, $max_x, $max_y, $max_value);
	$this->PrintTypeKey($id, $id_type);
	#$this->PrinDegreetKey($max_x,$max_y, $max_value);
	$this->PrintEnder();
    }
    
    if (defined $buffer) {
	if (defined $htmlcache) {
	    my $cgi = new CGI();
	    $htmlcache->printAndStore($cgi->header(-type=>'image/svg+xml'));
	    $htmlcache->printAndStore($buffer);
	} else {
	    return $buffer;
	}
    }
}
#######################

sub PrintCenter {
    my ($this, $min_x, $min_y, $max_x, $max_y) = @_;
    my $handle = $this->{handle};
    my $x = ($max_x-$min_x)/2+$min_x;
    my $y = ($max_y-$min_y)/2+$min_y;
    print $handle qq(<circle cx="$x" cy="$y" r="5" fill="black"/>\n);
}
    

sub PrintNodes {
    my ($this,$nodes) = @_;
    my $handle = $this->{handle};
    print $handle "<g id=\"Nodes\">\n";
    my %seen;
    my $type_display = $this->{type_display};
    my $sibling_display = $this->{sibling_display};
    my $url = "?mode0=as-core-image";
    $url = $this->{url} if (defined $this->{url});
    $url =~ s/\&/&#38;/g;
    foreach my $node (@$nodes) {

	my $type = $node->{type};
	next if (defined $type_display && !defined $node->{selected} && 
	    $type != $type_display);
	next if (defined $sibling_display && !defined $node->{sibling});
	$this->{type_count}{"asn"}{$type}++;

	my $size = $node->{size};
	my $x = $node->{x} - $size/2;
	my $y = $node->{y} - $size/2;
	my $name = $node->{name};
	$name = $node->{asn} unless (defined $name);
	my $color = $node->{color};

	next if (seen(\%seen,$size,$x,$y,$color));

	$name =~ s/\&/&amp;/g;
	my $asn = $node->{asn};
	my $value = $node->{value};
	my $title = "AS $asn ($value neighbors)";

	my $stroke_width = .5;
	if ($node->{selected}) {
	    $stroke_width = 2;
	}
	unless (defined $this->{pixel}) {
	    print $handle 
	    print $handle qq( <a xlink:href="$url&#38;as=$asn" target="_top">);
	}
	print $handle qq( <rect x="$x" y="$y" width="$size" height="$size")
		,qq( fill="$color" stroke="black" stroke-width="$stroke_width">\n);
	unless (defined $this->{pixel}) {
	    print $handle qq(   <title> $title </title>\n);
	}
	print $handle qq( </rect>);
	unless (defined $this->{pixel}) {
	    print $handle qq( </a>);
	}
    }
    print $handle "</g>\n";
}

sub PrintToolTip {
    my ($this) = @_;
    my $handle = $this->{handle};
print $handle <<EOP;
<!-- http://svg-whiz.com/svg/Tooltip2.svg -->
   <script type="text/ecmascript"><![CDATA[
      var SVGDocument = null;
      var SVGRoot = null;
      var SVGViewBox = null;
      var svgns = 'http://www.w3.org/2000/svg';
      var xlinkns = 'http://www.w3.org/1999/xlink';
      var toolTip = null;
      var TrueCoords = null;
      var tipBox = null;
      var tipText = null;
      var tipTitle = null;
      var tipDesc = null;

      var lastElement = null;
      var titleText = '';
      var titleDesc = '';


      function Init(evt)
      {
         SVGDocument = evt.target.ownerDocument;
         SVGRoot = SVGDocument.documentElement;
         TrueCoords = SVGRoot.createSVGPoint();

         toolTip = SVGDocument.getElementById('ToolTip');
         tipBox = SVGDocument.getElementById('tipbox');
         tipText = SVGDocument.getElementById('tipText');
         tipTitle = SVGDocument.getElementById('tipTitle');
         tipDesc = SVGDocument.getElementById('tipDesc');
         //window.status = (TrueCoords);

         //create event for object
         SVGRoot.addEventListener('mousemove', ShowTooltip, false);
         SVGRoot.addEventListener('mouseout', HideTooltip, false);
      };


      function GetTrueCoords(evt)
      {
         // find the current zoom level and pan setting, and adjust the
         // reported
         //    mouse position accordingly
         var newScale = SVGRoot.currentScale;
         var translation = SVGRoot.currentTranslate;
         TrueCoords.x = (evt.clientX - translation.x)/newScale;
         TrueCoords.y = (evt.clientY - translation.y)/newScale;
      };


      function HideTooltip( evt )
      {
         toolTip.setAttributeNS(null, 'visibility', 'hidden');
      };


      function ShowTooltip( evt )
      {
         GetTrueCoords( evt );

         var tipScale = 1/SVGRoot.currentScale;
         var textWidth = 0;
         var tspanWidth = 0;
         var boxHeight = 20;

         tipBox.setAttributeNS(null, 'transform', 'scale(' + tipScale + ',' + tipScale + ')' );
         tipText.setAttributeNS(null, 'transform', 'scale(' + tipScale + ',' + tipScale + ')' );

         var titleValue = '';
         var descValue = '';
         var targetElement = evt.target;
         if ( lastElement != targetElement )
         {
            var targetTitle = targetElement.getElementsByTagName('title').item(0);
            if ( targetTitle )
            {
               // if there is a 'title' element, use its contents for the
               // tooltip title
               titleValue = targetTitle.firstChild.nodeValue;
            }

            var targetDesc = targetElement.getElementsByTagName('desc').item(0);
            if ( targetDesc )
            {
               // if there is a 'desc' element, use its contents for the
               // tooltip desc
               descValue = targetDesc.firstChild.nodeValue;

               if ( '' == titleValue )
               {
                  // if there is no 'title' element, use the contents of
                  // the 'desc' element for the tooltip title instead
                  titleValue = descValue;
                  descValue = '';
               }
            }

            // if there is still no 'title' element, use the contents of
            // the 'id' attribute for the tooltip title
            if ( '' == titleValue )
            {
               titleValue = targetElement.getAttributeNS(null, 'id');
            }

            // selectively assign the tooltip title and desc the proper
            // values,
            //   and hide those which don't have text values
            //
            var titleDisplay = 'none';
            if ( '' != titleValue )
            {
               tipTitle.firstChild.nodeValue = titleValue;
               titleDisplay = 'inline';
            }
            tipTitle.setAttributeNS(null, 'display', titleDisplay );


            var descDisplay = 'none';
            if ( '' != descValue )
            {
               tipDesc.firstChild.nodeValue = descValue;
               descDisplay = 'inline';
            }
            tipDesc.setAttributeNS(null, 'display', descDisplay );
         }

         // if there are tooltip contents to be displayed, adjust the size
         // and position of the box
         if ( '' != titleValue )
         {
            var xPos = TrueCoords.x + (10 * tipScale);
            var yPos = TrueCoords.y + (10 * tipScale);

            //return rectangle around text as SVGRect object
            var outline = tipText.getBBox();
            tipBox.setAttributeNS(null, 'width', Number(outline.width) + 10);
            tipBox.setAttributeNS(null, 'height', Number(outline.height) + 10);

            // update position
            toolTip.setAttributeNS(null, 'transform', 'translate(' + xPos + ',' + yPos + ')');
            toolTip.setAttributeNS(null, 'visibility', 'visible');
         }
      };

   ]]></script>
EOP
}

sub PrintLinks {
    my ($this,$links) = @_;
    my $handle = $this->{handle};
    print $handle "<g id=\"Links\">\n";
    my %seen;
    my $type_display = $this->{type_display};
    my $sibling_display = $this->{sibling_display};
    foreach my $link (@$links) {
	my $type = $link->{type};
	next if (defined $type_display && !defined $link->{selected} && 
	    $type != $type_display);
	next if (defined $sibling_display && !defined $link->{sibling});
	$this->{type_count}{"link"}{$type}++;

	my $node0 = $link->{node0};
	my $node1 = $link->{node1};
	my $color = $link->{color};

	my $x1 = $node0->{x};
	my $y1 = $node0->{y};
	my $x2 = $node1->{x};
	my $y2 = $node1->{y};

	next if (seen(\%seen,$x1, $y1, $x2, $y2, $color));

	print $handle qq(    <line x1="$x1" y1="$y1" x2="$x2" y2="$y2" )
		," stroke=\"$color\" stroke-width=\"2\"/>\n";
    }
    print $handle "</g>\n";
}

use Data::Dumper;

sub PrintNames {
    my ($this, $min_x, $min_y, $max_x, $max_y, $nodes) = @_;
    my $handle = $this->{handle};

    my @selected;
    foreach my $node (@$nodes) {
	if (defined $node->{selected}) {
	    push @selected, $node;
	}
    }
    my @node_info;
    #foreach my $node (@$nodes) {
    foreach my $node (@selected) {
	my $size = $node->{size};
	my $x0 = $node->{x} - $size/2;
	my $y0 = $node->{y} - $size/2;
	my $x1 += $size;
	my $y1 += $size;
	push @node_info, {
	    "x0" => $x0,
	    "y0" => $y0,
	    "x1" => $x1,
	    "y1" => $y1
	    };
    }

    my $plot_x = ($max_x-$min_x)/2+$min_x;
    my $plot_y = ($max_y-$min_y)/2+$min_y;

    my @name_info;
    print $handle qq(<g id="Names">\n);
    #foreach my $node (reverse @$nodes) {
    foreach my $node (@selected) {
	my $size = $node->{size};
	my $x = $node->{x} - $size/2;
	my $y = $node->{y} - $size/2;
	my $name = $node->{name};
	next unless (defined $name);

	my @names = split /\s+/, $name;
	if ($#names > 0) {
	    $name = $names[0]." ".$names[1];
	}
	next unless (defined $name);

	my $value = $node->{weight};

	my $font_size = sprintf("%0.1f", 13*$size/MAX_SIZE);
	my $stroke_size = sprintf("%0.1f", .5*$size/MAX_SIZE)+2;
	next if ($font_size < 8);

	$name =~ s/Communication.*//;
	$name =~ s/-.*//;
	$name =~ s/,.*//;
	$name =~ s/\&/&amp;/g;
	$name =~ s/\?//g;
	$name =~ s/.+de Redes Colomsat S.A/Administracin de/g;

	#$name = "$node->{as} ($name)";

	my $center_x = $node->{x};
	my $center_y = $node->{y};
	my $color = $node->{color};

	my $theta = pi - atan2(($center_y-$plot_y),($center_x-$plot_x));
	my $name_info;
	my $overlap;

	my $width = 0;
	foreach my $char (split //, $name) {
	    if ($char =~ /[a-z]/) {
		$width += .4*$font_size;
	    } elsif ($char =~ /[A-z]/) {
		$width += .5*$font_size;
	    } else {
		$width += .4*$font_size;
	    }
	}
	my $height = .8*$font_size;

	$size *= .75;
	while ($theta < 2*pi) {
	    my $x = $center_x+ $size*cos($theta); 
	    my $y = $center_y+ $size*sin($theta); 
	    my $text_anchor = "start";
	    my $x0 = $x;
	    my $y0 = $y;
	    my $x1 = $x + $width;
	    my $y1 = $y + $height;
	    if ($x < $center_x) {
		$text_anchor = "end";
		$x0 = $x - $width;
		$x1 = $x;
	    }
	    $name_info = {
		"x" => $x,
		"y" => $y,
		"x0" => $x0,
		"y0" => $y0,
		"x1" => $x1,
		"y1" => $y1,
		"name"=>$name,
		"text_anchor" => $text_anchor
		};
	    $overlap = undef;
	    foreach my $i (@name_info, @node_info) {
		if (Overlap($i, $name_info)) {
		    $overlap =1;
		    last;
		}
	    }
	    unless (defined $overlap) {
		last;
	    }
	    $theta += .1*pi;
	}
	#unless (defined $overlap) {
	    $x = $name_info->{x};
	    $y = $name_info->{y};
	    my $text_anchor = $name_info->{text_anchor};
	    my $style = "text-anchor: $text_anchor;font-size:$font_size";
	    print $handle "    <g>\n";
	    print $handle qq(         <text x="$x" y="$y" fill="black" );
	    print $handle qq( style="stroke:white;stroke-width:$stroke_size;$style">);
	    print $handle qq( $name </text>\n);
	    print $handle qq(         <text x="$x" y="$y" fill="black" style="$style">);
	    print $handle qq( $name </text>\n);
#$x = $name_info->{x0};
#$y = $name_info->{y0};
#my $w = $name_info->{x1}-$name_info->{x0};
#my $h = $name_info->{y1}-$name_info->{y0};
#$y -= $h;
#print qq(<rect x="$x" y="$y" width="$w" height="$h" fill-opacity=".2" stroke="black" stroke-width="1" font="serif"></rect>\n);
	    print $handle "    </g>\n";
	    push @name_info, $name_info;
	#}
    }
    print $handle "</g>\n";
}

sub Overlap {
    my ($a,$b) = @_;
    return (($a->{x0} <= $b->{x0} && $b->{x0} <= $a->{x1}
	    || $a->{x0} <= $b->{x1} && $b->{x1} <= $a->{x1}
	    || $b->{x0} <= $a->{x0} && $a->{x0} <= $b->{x1})
	    &&
	  ($a->{y0} <= $b->{y0} && $b->{y0} <= $a->{y1}
	    || $a->{y0} <= $b->{y1} && $b->{y1} <= $a->{y1}
	    || $b->{y0} <= $a->{y0} && $a->{y0} <= $b->{y1}));
}

sub PrintDegreeKey {
    my ($this, $max_x, $max_y, $max_value) = @_;
    my $handle = $this->{handle};
    #print $handle " <text x=\"$x\" y=\"$y\" fill=\"black\" style=\"$style\">IPv4 AS Core (degree)</text>\n";

    my $key_width = $max_x/40;
    my $key_x_margin = $key_width*.1;
    my $key_x = $max_x + $key_x_margin;
    $max_x = $max_x + $key_x_margin + $key_width;

    my $key_height = 8*$max_y/10;
    my $key_y = ($max_y-$key_height)/2;

    my $NUM_BARS = 200;
    if ($max_value > 0 && $max_value < $NUM_BARS) {
	    $NUM_BARS = $max_value;
    }
    foreach my $value (0..$NUM_BARS) {
	my $fraction = $value/$NUM_BARS;
	my $color = $this->Value2Color($fraction);
	my $x = $key_x;
	my $width = $key_width;

	my $y = $key_y;
	my $height = $key_height*(1-$fraction);
	print $handle qq( <rect x="$x" y="$y" )
		.qq(width="$width" height="$height")
		,qq( fill="#$color" stroke-opacity="0" stroke-width="0">\n);
	print $handle qq(    <title> key </title>\n);
	print $handle qq( </rect>\n);
    }

    # The border
    print $handle qq( <rect x="$key_x" y="$key_y" width="$key_width" height="$key_height")
    ,qq( fill-opacity="0" fill="black" stroke="black" stroke-width="1">\n);
    print $handle qq(    <title> key_border </title>\n);
    print $handle qq( </rect>\n);

    foreach my $value (0..10) {
	my $fraction = $value/10;
	my $number = sprintf("%d",$max_value*$fraction);

	my $x1 = $key_x;
	my $y1 = $key_y + $key_height*(1-$fraction);

	my $x2 = $key_x + $key_width + 2*$key_x_margin;
	my $y2 = $y1;

	print $handle qq( <line x1="$x1" y1="$y1" x2="$x2" y2="$y2" )
		,qq(  stroke="#000000" stroke-width="1"/>\n);
	print $handle qq( <text x="$x2" y="$y2"> $number </text>\n);
    }
}

sub PrintContinents {
    my ($this, $min_x, $min_y, $max_x, $max_y, $max_value) = @_;
    my $handle = $this->{handle};
    my @continents = (
        {
            "name" => "North America",
            "lon_start" => "-168.3359374",
            "lon_end"  => "-56.8596442",
            "order" => 0,
            "color" => "pink"
        },
        {
            "name" => "South America",
            "lon_start" => "-83.710541",
            "lon_end"  => "-36.601166",
            "order" => 1,
            "color" => "lightgreen"
        },
        {
            "name" => "Europe",
            "lon_start" => "-9.882416",
            "lon_end"  => "33.711334",
            "order" => 0,
            "color" => "lightblue"
        },
        {
            "name" => "Africa",
            "lon_start" => "-16.3863222",
            "lon_end"  => "51.3773497",
            "order" => 1,
            "color" => "LightCoral"
        },
        {
            "name" => "Asia",
            "lon_start"  => "33.711334",
            "lon_end"  => "190",
            "order" => 0,
            "color" => "gainsboro"
        },
        {
            "name" => "Oceania",
            "lon_start" => "94.2728129",
            "lon_end"  => "180",
            "order" => 1,
            "color" => "moccasin"
        }
        );

    print $handle "<g id=\"Continents\">\n";
    my $x_center = ($max_x-$min_x)/2 + $min_x;
    my $y_center = ($max_y-$min_y)/2 + $min_y;
    #my ($radius) = XY($max_value, 1, 0);
    my $radius = RADIUS;
    foreach my $continent (@continents) {
        my $name = $continent->{name};
        my @lon = ($continent->{lon_start}, $continent->{lon_end});
        my $color = $continent->{color};
	my $shift = $max_value*1.1*$continent->{order};

	my $font_size = sprintf("%0.1f", 2*MAX_SIZE);

	my @x;
	my @y;
	my $r = $radius + $continent->{order}*(.5*MARGIN_RIGHT);
	foreach my $i (0..1) {
	    my $angle = -2*3.14*($lon[$i]/360);
	    $x[$i] = $x_center + $r* cos($angle);
	    $y[$i] = $y_center + $r* sin($angle);
	}

        my $large_arch_flag = 0;
        my $sweep_flag = 0;
	my $theta_delta = ($lon[1] - $lon[0])/180;
        if ($theta_delta > pi) {
            $large_arch_flag = 1;
        }

	
	my $r_name = $r-.015*$radius;
	my $name_center = ($lon[1]+$lon[0])/2;
	my $angle = -2*3.14*($name_center/360);
	my $rotate = 90-$name_center;
	while ($rotate < 0) { $rotate += 360; }
	
	my $x_name = $x_center + $r_name* cos($angle);
	my $y_name = $y_center + $r_name* sin($angle);

	print $handle <<EOP;
    <path d=" M$x[0],$y[0] A$r,$r 0 $large_arch_flag,$sweep_flag $x[1],$y[1]"
	style="stroke:$color;fill:none;stroke-width:20"/>
    <text x="$x_name" y="$y_name" style="font-family:Super Sans;font-size:$font_size;text-anchor:middle;font-weight:bold;" 
	transform="rotate($rotate $x_name $y_name)" fill="black">$name</text>
EOP
    }
    print $handle "</g>\n";

}

########################################################################


sub PrintHeader {
    my ($this, $min_x, $min_y, $max_x, $max_y) = @_;
    my $handle = $this->{handle};
    my $width = WIDTH;
    my $height = HEIGHT;
    my $width_string = $width."px";
    my $height_string = $height."px";
    print $handle <<EOP;
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
	xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1"
	width="$width_string" height="$height_string">
EOP
	
    my $target_width = $this->{target_width};
    if (defined $target_width && !defined $this->{pixel}) {
	my $scale = $target_width/$width;
	print $handle "<g transform=\"scale($scale,$scale)\">\n";
    }
}

sub PrintTypeKey {
    my ($this, $id, $id_type) = @_;
    my $handle = $this->{handle};

    my $font_family="Helvetica";
    my $font_size = sprintf("%0.1f", 2.5*MAX_SIZE);
    my $style = "font-size:$font_size;font-family:$font_family";
    my $x = 20;
    my $y = 1*$font_size;
    my $num_errors = @{$this->{errors}};
    if (defined $id) {
	my $name = "AS $id";
	if ($id_type == ID_ORG) {
	    my ($org_name) = Org->getName($id);
	    if (defined $org_name) {
		$name = $org_name;
	    } else {
		$name = $id;
	    }
	}
	print $handle qq( <text x="$x" y="$y" fill="black" style="$style;font-weight:bold" transform="rotate\(0,0\)"> $name </text>);

	#my $x1 = $x+(.15*$font_size*length($name));
	my $x0 = $x;
	my $x1 = 430;
	$y += .2*$font_size;
	print $handle qq( <line x1="$x0" y1="$y" x2="$x1" y2="$y" )
		,qq(  stroke="#000000" stroke-width="3"/>\n);

	my @size_color_strings = ([int(.7*$font_size), "white",
	    "type", "num.ASes", "num.links"]);
	foreach my $type (sort {$a<=>$b} keys %type_name) {
	
	    next if ($type == SELECTED);
	    my $count_as = $this->{type_count}{"asn"}{$type};
	    my $count_link = $this->{type_count}{"link"}{$type};
	    next if (!defined $count_as && !defined $count_link);
	    $count_as = 0 unless (defined $count_as);
	    $count_link = 0 unless (defined $count_link);

	    my $name = $type_name{$type};
	    my $color = $type_color{$type};
	    push @size_color_strings, [$font_size, $color, $name, $count_as, 
		$count_link];
	}

	my @lengths;
	foreach my $size_color_strings (@size_color_strings) {
	    my ($font_size_name, $color, @strings) = @$size_color_strings;
	    foreach my $i (0..$#strings) {
		my $len = length($strings[$i]);
		if (!defined $lengths[$i] || $lengths[$i] < $len) {
		    $lengths[$i] = $len;
		}
	    }
	}

	$y += .1*$font_size;
	foreach my $size_color_strings (@size_color_strings) {
	    my ($font_size_name, $color, @strings) = @$size_color_strings;
	    my $box_width = .8*$font_size;
	    my $box_y = $y + .2*$font_size;
	    my $box_height = .8*$font_size;
	    my $stroke = "none";
	    my $stroke_width = 0;
	    
	    $style = "font-size:$font_size;font-family:$font_family";
	    print $handle qq( <rect x="$x" y="$box_y" width="$box_width" height="$box_height")
		    ,qq( fill="$color" stroke="$stroke" stroke-width="$stroke_width"></rect>\n);

	    my $x1 = $x + 1.1*$font_size;
	    $y += $font_size;
	    foreach my $i (0..$#strings) {
		print $handle qq( <text x="$x1" y="$y" fill="black" style="$style")
		    ,qq( transform="rotate\(0,0\)">$strings[$i] </text>\n);
		$x1 += .8*$font_size*$lengths[$i];
	    }
	}
    }
}

sub PrintEnder() {
    my ($this) = @_;
    my $handle = $this->{handle};
    my $target_width = $this->{target_width};
    if (defined $target_width && !defined $this->{pixel}) {
	print $handle "</g>\n";
    }
    print $handle <<EOP;
</svg>
EOP
}

#############################################################

my %count; # count the frequency of the above event

sub seen {
    my ($seen, @keys) = @_;
    my $seen_id = "";
    foreach my $key (@keys) {
	if ($key =~ /^[-\d\.]+$/) {
	    $key = SigNum($key, 2);
	}
	$seen_id .= "\0".$key;
    }
    return if (defined $seen->{$seen_id});
    $seen->{$seen_id} = 1;
    return;
}

sub SigNum {
	use POSIX;
	my ($num, $sig) = @_;
	my $neg;
	if ($num < 0) {
	    $num *= -1;
	    $neg = 1;
	}
	return 0 if ($num == 0);
	$sig = 4 unless (defined $sig);
	my $exponent = floor(log($num)/log(10))+1-$sig;
	my $value = ($num/10**($exponent-2));
	$value -= $value%100;
	$value = floor($value/100)*10**$exponent;
	if (defined $neg) {
	    $value *= -1;
	}
	return $value;
}


#############################################################

sub SetUp {
    my ($this, $id, $id_type) = @_;

    my ($max_value, $nodes, $links);
    if (defined $id) {
	($max_value, $nodes, $links) = $this->SetUpId($id, $id_type);
    } else  {
	($max_value, $nodes, $links) = $this->SetUpAll();
    }
    return unless (defined $max_value);

    my ($min_x, $max_x, $min_y, $max_y);
    foreach my $lon (0, 90, 180, -90) {
	my ($x, $y, $size) = XY($max_value, 1, $lon);
	unless (defined $min_x) {
	    $min_x = $x;
	    $max_x = $size + $x;
	} elsif ($x < $min_x) {
	    $min_x = $x;
	} elsif ($x+$size > $max_x) {
	    $max_x = $x+$size;
	}
	unless (defined $min_y) {
	    $min_y = $y;
	    $max_y = $size + $y;
	} elsif ($y < $min_y) {
	    $min_y = $y;
	} elsif ($y+$size > $max_y) {
	    $max_y = $y+$size;
	}
    }

    foreach my $node (@$nodes) {
	my $value = $node->{value};
	my ($x, $y, $size) = XY($max_value, $value, $node->{longitude});

	$node->{x} = $x;
	$node->{y} = $y;
	if (defined $node->{selected}) {
	    $node->{size} = 1.3*MAX_SIZE;
	} else {
	    $node->{size} = $size;
	}
    }
#while ($#nodes > 100) { shift @nodes; }

#while ($#links > 100) { shift @links; }
    return ($min_x, $min_y, $max_x, $max_y, $max_value, $nodes, $links);
}

sub SetUpAll {
    my ($this) = @_;
    $this->LoadLoc();
    $this->LoadValues();
    $this->LoadLinks();
    my $max_value = AS->getMaxConeNumberAses();
    my $sort_type = $this->{sort_type};
    my @nodes;
    foreach my $asn (keys %{$this->{asn2nodes}}) {
	my $node = $this->{asn2nodes}{$asn};
	my $value = $node->{$sort_type};
	my $lon = $node->{lon};
	if (defined $value && defined $lon) {
	    push @nodes, $node;
	    $node->{value} = $value;
	    $node->{color} = $this->Value2Color($value/$max_value);
	}
    }
    @nodes = sort {$a->{value}<=>$b->{value}} @nodes;

    my @links;
    foreach my $link (@{$this->{links}}) {
	my $asn0_value = $link->{asn0}{value};
	my $to_value = $link->{asn1}{value};
	next unless (defined $asn0_value && defined $to_value);
	push @links, $link;
	my $value;
	if ($asn0_value < $to_value) {
	    $value = $asn0_value;
	} else {
	    $value = $to_value;
	}
	$link->{value} = $value;
	$link->{color} = $this->Value2Color($value/$max_value);
    }
    @links = sort {$a->{value}<=>$b->{value}} @links;
    return ($max_value, \@nodes, \@links);
}

sub SetUpId {
    my ($this, $id, $id_type) = @_;

    my $max_value = AS->getMaxConeNumberAses();
    unless (defined $max_value) {
	die("Failed to get a max_value");
    }

    my %members;
    my %siblings;
    if ($id_type == ID_AS) {
	$members{$id} = 1;
        my $sibling_display = $this->{sibling_display};
        if (defined $sibling_display) {
            foreach my $sibling (AS->getSiblings($id)) {
                $siblings{$sibling} = 1;
            }
        }
    } else {
	foreach my $info (Org->getMembers($id)) {
	    $members{$info->{asn}} = 1;
	}
    }
    
    my @nodes;
    my @missing;
    foreach my $asn (keys %members) {
	my $node = $this->CreateNode($asn, SELECTED, 1);
	if (defined $node) {
	    push @nodes, $node;
	    $members{$asn} = $node;
	} else {
	    delete $members{$asn};
	    push @missing, $asn;
	}
    }

    my $num_members = keys %members;
    if ($num_members < 1) {
	$this->Error("Failed to find any coordinates for asnes:".join(",",@missing));
	$this->PrintErrors();
    }

    my @links;
    foreach my $link (AS->getLinks() ) {
	my $asn0 = $link->{asn0};
	my $asn1 = $link->{asn1};
	my $type = $link->{type};
	my $node0 = $members{$asn0};
	my $node1 = $members{$asn1};
	if (defined $node0 && defined $node1) {
	    my $value = $node0->{value};
	    my $value1 = $node1->{value};
	    if ($value < $value1) {
		$value = $value1;
	    }
	    push @links, $this->CreateLink($node0, $node1, $value, SIBLING, SIBLING);
	} else {
	    if (defined $node1) {
		($asn0, $asn1) = ($asn1,$asn0);
		($node0, $node1) = ($node1, $node0);
		$type = -1*$type;
	    }
	    if (defined $node0) {
		my $sibling = $link->{sibling};
		$node1 = $this->CreateNode($asn1, $type, $sibling);
		if (defined $node1) {
		    push @links, $this->CreateLink($node0, $node1, $node1->{value}, $type, $sibling);
		    push @nodes, $node1;
		}
	    }
	}
    }

    @nodes = sort {$a->{type}<=>$b->{type}} @nodes;
    @links = sort {$a->{type}<=>$b->{type}} @links;

    return ($max_value, \@nodes, \@links);
}

sub CreateNode {
    my ($this, $asn, $type, $sibling) = @_;
    my $node = $this->{asn2node}{$asn};
    return $node if (defined $node);

    my ($lat, $lon) = AS->getAsnGeo($asn);
    unless (defined $lon && $lon =~ /^-?\d*(.\d*)?$/) {
	#$this->Error("Failed to find coordinates for AS $asn");
	return;
    }

    my ($num_ases, $num_prefixes, $num_addresses) =
	AS->getAsnCustomerCone($asn);
    unless (defined $num_ases) {
	#$this->Error("failed to find cone for $asn");
	return;
    }
    $node = {
	"asn" => $asn,
	"name" => $asn,
	"selected" => ($type == SELECTED) ? 1 : undef,
	"latitude" => $lat,
	"longitude" => $lon,
	"type" => $type,
	"sibling" => $sibling,
	"value" => $num_ases,
	"color" => $type_color{$type}
	};
    $this->{asn2node}{$asn} = $node;
    return $node;
}

sub CreateLink {
    my ($this, $node0, $node1, $value, $type, $sibling) = @_;
    return {  
	"node0" => $node0,
	"node1" => $node1,
	"value" => $value,
	"type" => $type,
	"sibling" => $sibling,
	"color" => $type_color{$type}
	};
}

=cut
sub SetUpId {
    my ($this, $id, $id_type) = @_;

    my $max_value = AS->getMaxConeNumberAses();
    unless (defined $max_value) {
	die("Failed to get a max_value");
    }

    my @nodes;
    my @selected;
    my @selected_links;
    my @links;
    my @neighbors;
    my %asn2node;
    my %siblings;
    if ($id_type == ID_AS) {
	my ($lat, $lon) = AS->getAsnGeo($id);
	unless (defined $lon && $lon =~ /^-?\d*(.\d*)?$/) {
	    $this->Error("Failed to find coordinates for AS $id");
	    return;
	}

	my ($number_asnes, $num_prefixes, $num_addresses) =
	    AS->getAsnCustomerCone($id);
	unless (defined $number_asnes) {
	    $this->Error("failed to find cone for $id");
	    return;
	}
	my $asn = $id;
	my $node = {
	    "asn" => $asn,
	    "name" => $asn,
	    "selected" => 1,
	    "latitude" => $lat,
	    "longitude" => $lon,
	    "type" => SELECTED,
	    "sibling" => 1,
	    "value" => $number_asnes,
	    "color" => $type_color{SELECTED.""}
	    };
	$asn2node{$asn} = $node;
	push @selected, $node;

	my $sibling_display = $this->{sibling_display};
	if (defined $sibling_display) {
	    foreach my $sibling (AS->getSiblings($id)) {
		$siblings{$sibling} = 1;
	    }
	}

	@neighbors = AS->getNeighborsGeoCustomerCone($id);
    } else {
	my @org_as = reverse sort {$a->{number_asnes}<=>$b->{number_asnes}} 
	    Org->getGeoCustomerCone($id);
	foreach my $org_as (@org_as) {
	    my $asn = $org_as->{asn};
	    my $lon = $org_as->{longitude};
	    my $value = $org_as->{number_asnes};
	    if (defined $lon && defined $value) {	
		my $node = {
		    "asn" => $asn,
		    "name" => $asn,
		    "selected" => 1,
		    "longitude" => $org_as->{longitude},
		    "value" => $org_as->{number_asnes},
		    "type" => SIBLING,
		    "sibling" => 1,
		    "color" => $type_color_node{SELECTED.""}
		};
		$asn2node{$asn} = $node;
		push @selected, $node;
	    }
	}
	if ($#selected < 0) {
	    $this->Error("org $id does not contain any ASes with geo/cone");
	    return;
	}
	my $sibling_color = $type_color_node{SIBLING.""};
	my @sibling_links = Org->getSiblingLinks($id);
	foreach my $link (@sibling_links) {
	    my $asn0 = $link->{asn0};
	    my $asn1 = $link->{asn1};

	    my $node0 = $asn2node{$asn0};
	    my $node1 = $asn2node{$asn1};
#print "$node0 $node1\n";
	    if (defined $node0 && defined $node1) {
		push @selected_links, {
		    "node0" => $node0,
		    "node1" => $node1,
		    "value" => SIBLING,
		    "type" => SIBLING,
		    "sibling" => 1,
		    "color" => $sibling_color
		    };
	    }
	}
	@neighbors = Org->getNeighborsGeoCustomerCone($id);
    }
    @neighbors = sort {
	    if ($a->{type} == $b->{type}) {
		return 0;
	    } elsif ($a->{type} == 0) {
		return -1;
	    } elsif ($b->{type} == 0) {
		return 1;
	    }
	    return $a->{type}<=>$b->{type};
	} @neighbors;

    foreach my $neighbor (@neighbors) {
	my ($node0, $node1);
	my $type = $neighbor->{type};
	my $color = $type_color_node{$type};
	my $value = $neighbor->{number_asnes};
	if ($id_type == ID_AS) {
	    my $asn0 = $selected[0];
	    my $asn1 = $neighbor->{asn};
	    my $lon = $neighbor->{longitude};
	    if (defined $value && defined $lon) {
		$node1 = {
		    "asn" => $asn1,
		    "longitude" => $lon,
		    "color" => $color,
		    "type" => $type,
		    "value" => $value
		    };
		if (defined $siblings{$asn1}) {
		    $node1->{sibling} = 1;
		}
		push @nodes, $node1;
	    } 
	} else {
	    $node0 = $asn2node{$neighbor->{asn0}};
	    next unless( defined $node0);

	    my $asn1 = $neighbor->{asn1};
	    $node1 = $asn2node{$asn1};
	    unless (defined $node1) {
		my $lon = $neighbor->{"longitude"};
		$node1 = {
		    "asn" => $asn1,
		    "longitude" => $lon,
		    "color" => $color,
		    "type" => $type,
		    "value" => $value
		    };
		$asn2node{$asn1} = $node1;
		push @nodes, $node1;
	    } elsif ($node1->{type} != SELECTED && $node1->{type} < $type) {
		$node1->{type} = $type;
		$node1->{color} = $color;
	    }
	}
#print STDERR "$node0 $node1\n";
	if (defined $node0 && defined $node1) {
	    my $value = $neighbor->{number_asnes};
	    #if ($type == PROVIDER) {
	#	$node->{name} = $as_n;
	#    }
	    my $link = {
		"node0" => $node0,
		"node1" => $node1,
		"value" => $value,
		"type" => $type,
		"color" => $color
		};
	    if (defined $node0->{sibling} && defined $node1->{sibling}) {
		$link->{sibling} = 1;
	    }
	    push @links, $link;
	}
    }
    push @nodes, @selected;
    push @links, @selected_links;

    return ($max_value, \@nodes, \@links);
}
=cut

sub XY {
    my ($max_value, $value, $lon) = @_;
    my $angle = -2*3.14*($lon/360);
    my $radius_max = log($max_value+1) - log(1) +.5;
    my $scale = RADIUS/$radius_max;
	
    my $radius = $scale*(log($max_value+1) - log($value+1) +.5);
    my $size = int((MAX_SIZE-3)* (log($value+1)/log($max_value+1)) )+3;

    my $x = ($radius * cos ($angle)) + RADIUS + MARGIN_LEFT;
    my $y = ($radius * sin ($angle)) + RADIUS + MARGIN_RIGHT;
    return ($x, $y, $size);
}

########################################################################

sub Error {
    my ($this, $message) = @_;
    push @{$this->{errors}}, $message;
}

sub PrintErrors {
    my ($this) = @_;
    my $handle = $this->{handle};
    my @errors = @{$this->{errors}};
    my $font_size = sprintf("%0.1f", 1.7*MAX_SIZE);
    my $min_x = 0;
    my $min_y = 0;
    my $max_x = 100;
    foreach my $error (@errors) {
	my $len = .5*$font_size *(length($error)+2);
	if ($len > $max_x) {
	    $max_x = $len;
	}
    }
    my $max_y = $font_size*($#errors + 2);
    $this->PrintHeader(0,0, WIDTH, WIDTH);

    my $x = $font_size;
    my $y = 1.5*$font_size;
    my $style = "font-size:$font_size";
    foreach my $error (@errors) {
	print $handle " <text x=\"$x\" y=\"$y\" fill=\"red\" style=\"$style\">";
	print $handle $error;
	print STDERR $error,"\n";
	print $handle "</text>\n";
	$y *= $font_size;
    }
    $this->PrintEnder();
}

sub SetGrayScale() {
    my ($this) = @_;
    $this->{grayscale} = 1;
}

sub Value2Color {
	my ($this, $input) = @_;
	my $grayscale = $this->{grayscale};
	my ($hue, $sat, $bri);

	if ($input <= 0.000001) {
		$input = .000001;
	}
	my $temp = log( (120*$input)+1)/log(121);
	unless (defined $grayscale) {
		$hue = (4+5*$temp)/8;
		$sat = 100;
		$bri = 100;
	} else {
		$hue = 1;
		$sat = 0;#100*$temp;
		$bri = 80*$temp+20;
	}
	my ($r, $g, $b) = hsv2rgb(360*$hue, $sat, $bri);
	foreach my $v ($r, $g, $b) {
		$v = sprintf ("%x", $v);
		$v = "0$v" if (length ($v) < 2);
	}
	return "$r$g$b";
}

sub hsv2rgb {
  my ($h, $s, $v) = @_;
  my ($r, $g, $b);

  $h = 0 if $h < 0;
  $h -= 360 if $h >= 360;
  $h /= 60;

  my $f = ($h - int $h) * 255;

  $s /= 100;
  $v /= 100;

  if (int $h == 0) {
	$r = $v * 255;
	$g = $v * (255 - ($s * (255 - $f)));
	$b = $v * 255 * (1 - $s);
  }
  if (int $h == 1) {
	$r = $v * (255 - $s * $f);
	$g = $v * 255;
	$b = $v * 255 * (1 - $s);
  }
  if (int $h == 2) {
	$r = $v * 255 * (1 - $s);
	$g = $v * 255;
	$b = $v * (255 - ($s * (255 - $f)));
  }
  if (int $h == 3) {
	$r = $v * 255 * (1 - $s);
	$g = $v * (255 - $s * $f);
	$b = $v * 255;
  }
  if (int $h == 4) {
	$r = $v * (255 - ($s * (255 - $f)));
	$g = $v * (255 * (1 - $s));
	$b = $v * 255;
  }
  if (int $h == 5) {
	$r = $v * 255;
	$g = $v * 255 * (1 - $s);
	$b = $v * (255 - $s * $f);
  }
  return ($r, $g, $b);
}
1;

