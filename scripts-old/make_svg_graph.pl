#!/usr/bin/env perl
#
#   This program does the a circle placement algorithm which
#	INPUT:
#	    links file - a listing of all the links with each
#		line in the file being a link.
#		    from to wieght
#			from - the source of the link
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

use Getopt::Std;
use Socket;
 use Math::Trig;
use strict;

use constant MAX_SIZE => 18;

my ($exicutable) = ($0 =~ /([^\/]+)$/);
my $usage = "usage:$exicutable [-hmgk] [-a radius-alg] [-t type-sort] [-N name_limit] "
	."[-r rank_file] [-n name_file] -l loc_file links_file";

my $alg_default = "log";
my @alg_all = qw(log linear);
my $algs = join(", ", @alg_all);

my $type_sort_default = "transitdegree";
my @types_degree = qw( outdegree indegree transitdegree globaldegree);
my @types_rank = qw( rank count_24 count_prefix count_as count_degree);
my @types_all = (@types_degree, @types_rank);
my $types = join(", ", @types_all);

sub Help {
print<<EOP;
$usage
	-a algorithm-radius - this sets the algrithm for setting the radius.
	values: $algs
	default: $alg_default
	-t type-sorter - this is the type that will be used to sort
	values: $types
	default:$type_sort_default
	-N name_limit - this is the lowest value for which
	the added NAME field in the recs file will be
	added to the name of the as when displayed by otter
	-r rank_file - a ASCII dump from as-rank.caida.org
	-n name_file - stores as names
	-f names of as less size

	as name
	-i as2info file - another source for names, shares format with as-rank
	-l loc_file - the location file
	as continent country region city lat long total-prefixes
	-m print missing ASes
	-g sets it to use grayscale
	-k generate a color key
	links_file
	as_from as_to
EOP
}

my %opts;
if (!getopts("hgka:t:N:r:n:l:i:mc:f:",\%opts) ||
	($#ARGV < 0 && !defined $opts{h}) ) {
	print STDERR $usage,"\n";
	exit -1;
}
if (defined $opts{h}) {
	Help();
	exit;
}

my $missing_print = $opts{m};
my $grayscale = $opts{g};
my $print_key = $opts{k};
my $name_filter = $opts{f};
my $use_outdegree = 1;

my %as2Degree; #Map of ASes and their transit degrees


use vars qw( %as2rec %nodes %link2rec %links);
my ($alg_radius, $type_sort, $name_limit, $rank_file, $name_file,
	$loc_file, $links_file) = ParseARGV();
my $as2info_file = $opts{i};

if (defined $rank_file) {
	LoadRank($rank_file);
}
if (defined $name_file) {
	LoadName($name_file);
}
if (defined $as2info_file) {
	LoadAsInfo($as2info_file);
}
LoadLoc($loc_file);
LoadData($links_file);
my ($min_x, $min_y, $max_x, $max_y, $max_value) = SetUpPosition();
print STDERR "max_x:$max_x max_y:$max_y\n";
PrintGraph($min_x,$min_y,$max_x,$max_y, $max_value);
PrintCount();

sub ParseARGV {

	my $alg_radius = $opts{'a'};
	my $type_sort = $opts{'t'};
	my $name_limit = $opts{'N'};
	my $rank_file = $opts{'r'};
	my $name_file = $opts{'n'};
	my $loc_file = $opts{'l'};

	$alg_radius = $alg_default unless (defined $alg_radius);
	CheckValueInValues($alg_radius, @alg_all);

	$type_sort = $type_sort_default unless (defined $type_sort);
	CheckValueInValues($type_sort, @types_all);

	unless (defined $loc_file) {
		print STDERR $usage,"\n";
		print STDERR "    no location file specified\n";
		exit -1;
	}
	my $links_file = $ARGV[0];
	return ($alg_radius, $type_sort, $name_limit, $rank_file, $name_file,
	$loc_file, $links_file);
}

sub CheckValueInValues {
	my ($value, @values) = @_;
	my $value_found;
	foreach my $value_valid (@values) {
		if ($value eq $value_valid) {
			$value_found = 1;
		}
	}
	unless (defined $value_found) {
		print STDERR $usage,"\n";
		print STDERR "   $value not found in ",join(",",@values),"\n";
		exit -1;
	}
}

sub PrintGraph {
	my ($min_x, $min_y, $max_x, $max_y, $max_value) = @_;

	my @nodes = sort {$as2rec{$a}{$type_sort}<=>$as2rec{$b}{$type_sort}}
	keys %nodes;
	my @links =  sort 
	    {$link2rec{$a}{$type_sort}<=>$link2rec{$b}{$type_sort}}
	    keys %link2rec;
	my $num_links = @links;

#while ($#nodes >= 100) { shift @nodes; }
	PrintHeader($min_x,$min_y,$max_x,$max_y);
print STDERR "PrintLinks\n";
	PrintLinks(@links);
print STDERR "PrintNodes\n";
	PrintNodes(@nodes);
	if (defined $name_file) {
print STDERR "PrintNames\n";
	    PrintNames(@nodes);
	}
	if (defined $print_key) {
print STDERR "Printkeys\n";
		$max_x = PrintKey($max_x,$max_y, $max_value);
	}
print STDERR "PrintEnder\n";
	PrintEnder();
}

sub PrintNodes {
    my @nodes = @_;
    print "<g id=\"Nodes\">\n";
    foreach my $as (@nodes) {
	my $size = $as2rec{$as}{size};
	my $x = $as2rec{$as}{x} - $size/2;
	my $y = $as2rec{$as}{y} - $size/2;
	my $color = $as2rec{$as}{color};

	next if (seen("nodes",$size,$x,$y,$color));

	my $name = $as2rec{$as}{name};
	$name =~ s/\&/&amp;/g;
	my $as_name = $as;
	$as_name = "$as ($name)" if ($name =~ /[^\s]/);
	my $value = $as2rec{$as}{$type_sort};
	$as_name .= " [$value]\n";

	print qq( <a xlink:href="as=$as">);
	print qq( <rect x="$x" y="$y" width="$size" height="$size")
		,qq( fill="#$color" stroke="black" stroke-width=".5">\n);
	print qq(    <title> $as_name </title>\n);
	print qq( </rect>);
	print qq( </a>);
    }
    print "</g>\n";
}

sub PrintNames {
    my @nodes = @_;

    my @node_info;
    foreach my $as (@nodes) {
	my $size = $as2rec{$as}{size};
	my $x0 = $as2rec{$as}{x} - $size/2;
	my $y0 = $as2rec{$as}{y} - $size/2;
	my $x1 += $size;
	my $y1 += $size;
	push @node_info, {
	    "x0" => $x0,
	    "y0" => $y0,
	    "x1" => $x1,
	    "y1" => $y1
	    };
    }
    my @name_info;
    print qq(<g id="Names">\n);
    my @as = reverse @nodes;
    foreach my $index (0..$#as) {
	my $as = $as[$index];
	my $name = $as2rec{$as}{name};
	my @names = split /\s+/, $name;
	if ($#names > 0) {
	    $name = $names[0]." ".$names[1];
	}
	next unless (defined $name);

	my $value = $as2rec{$as}{$type_sort};
	next if (defined $name_filter && $value < $name_filter);

	my $size = $as2rec{$as}{size};
	my $font_size = sprintf("%0.1f", 17*$size/MAX_SIZE);
	my $stroke_size = sprintf("%0.1f", .5*$size/MAX_SIZE)+2;

	$name =~ s/Communication.*//;
	$name =~ s/-.*//;
	$name =~ s/,.*//;
	$name =~ s/\&/&amp;/g;
	$name =~ s/\?//g;
	$name =~ s/.+de Redes Colomsat S.A/Administracin de/g;

	$name = "$as ($name)";

	my $center_x = $as2rec{$as}{x};
	my $center_y = $as2rec{$as}{y};
	my $color = $as2rec{$as}{color};

	my $theta = 0;
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
	unless (defined $overlap) {
	    my $x = $name_info->{x};
	    my $y = $name_info->{y};
	    my $text_anchor = $name_info->{text_anchor};
	    my $style = "text-anchor: $text_anchor;font-size:$font_size";
	    print "    <g>\n";
	    print qq(         <text x="$x" y="$y" fill="black" );
	    print qq( style="stroke:white;stroke-width:$stroke_size;$style">);
	    print qq( $name </text>\n);
	    print qq(         <text x="$x" y="$y" fill="black" style="$style">);
	    print qq( $name </text>\n);
#$x = $name_info->{x0};
#$y = $name_info->{y0};
#my $w = $name_info->{x1}-$name_info->{x0};
#my $h = $name_info->{y1}-$name_info->{y0};
#$y -= $h;
#print qq(<rect x="$x" y="$y" width="$w" height="$h" fill-opacity=".2" stroke="black" stroke-width="1" font="serif"></rect>\n);
	    print "    </g>\n";
	    push @name_info, $name_info;
	}
    }
    print "</g>\n";
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
	


sub PrintLinks {
    my @links = @_;
    print "<g id=\"Links\">\n";
    foreach my $link (@links) {
	my $from = $link2rec{$link}{from};
	my $to = $link2rec{$link}{to};
	my $color = $link2rec{$link}{color};

	my $x1 = $as2rec{$from}{x};
	my $y1 = $as2rec{$from}{y};
	my $x2 = $as2rec{$to}{x};
	my $y2 = $as2rec{$to}{y};

	next if (seen("links",$x1, $y1, $x2, $y2, $color));

	print qq(    <line x1="$x1" y1="$y1" x2="$x2" y2="$y2" )
		," stroke=\"#$color\" stroke-width=\".5\"/>\n";
    }
    print "</g>\n";
}

sub PrintKey {
	my ($max_x, $max_y, $max_value) = @_;

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
		my $color = Value2Color($fraction);
		my $x = $key_x;
		my $width = $key_width;

		my $y = $key_y;
		my $height = $key_height*(1-$fraction);
		print qq( <rect x="$x" y="$y" )
			.qq(width="$width" height="$height")
			,qq( fill="#$color" stroke-opacity="0" stroke-width="0">\n);
		print qq(    <title> key </title>\n);
		print qq( </rect>\n);
	}

	# The border
	print qq( <rect x="$key_x" y="$key_y" width="$key_width" height="$key_height")
	,qq( fill-opacity="0" fill="black" stroke="black" stroke-width="1">\n);
	print qq(    <title> key_border </title>\n);
	print qq( </rect>\n);

	foreach my $value (0..10) {
		my $fraction = $value/10;
		my $number = sprintf("%d",$max_value*$fraction);

		my $x1 = $key_x;
		my $y1 = $key_y + $key_height*(1-$fraction);

		my $x2 = $key_x + $key_width + 2*$key_x_margin;
		my $y2 = $y1;

		print qq( <line x1="$x1" y1="$y1" x2="$x2" y2="$y2" )
			,qq(  stroke="#000000" stroke-width="1"/>\n);
		print qq( <text x="$x2" y="$y2"> $number </text>\n);
	}
}

#############################################################

my %seen;  # this is used to skip nodes which had already been printed
my %count; # count the frequency of the above event

sub seen {
	my ($object, @keys) = @_;
	my $seen_id = "";
	foreach my $key (@keys) {
		if ($key =~ /^[-\d\.]+$/) {
			$key = SigNum($key, 3);
		}
		$seen_id .= "\0".$key;
	}
	
	if (defined $seen{$seen_id}) {
		$count{$object}{"skipped"}++;
		return 1;
	}
	$count{$object}{"printed"}++;
	$seen{$seen_id} = 1;
	return;
}

sub SigNum {
	use POSIX;
	my ($num, $sig) = @_;
	return 0 if ($num == 0);
	$sig = 4 unless (defined $sig);
	my $exponent = floor(log($num)/log(10))+1-$sig;
	my $value = ($num/10**($exponent-2));
	$value -= $value%100;
	return floor($value/100)*10**$exponent;
}

sub PrintCount {
	print STDERR "Links and ASes with the same x,y corrodinates are skipped.\n";
	print STDERR "Since they will hidden by removing them significantly\n";
	print STDERR "reduces the number of objects in the file.\n";
	foreach my $object (sort keys %count) {
		foreach my $type (sort keys %{$count{$object}}) {
			print STDERR "$object $type $count{$object}{$type}\n";
		}
	}
}


#############################################################

sub SetUpPosition {
	my $max_value;
	foreach my $as (keys %nodes) {
		my $value = $as2rec{$as}{$type_sort};
		$value = $as2rec{$as}{$type_sort} = 0 unless (defined $value);
		if ($value > $max_value) {
			$max_value = $value;
		}
	}
	print STDERR "max_value:$max_value\n";

	my ($min_x, $max_x, $min_y, $max_y);
	foreach my $as (keys %nodes) {
		my $value = $as2rec{$as}{$type_sort};
		my $angle = -2*3.14*($as2rec{$as}{"LONG"}/360);
		my $radius;
		if ($alg_radius eq "linear") {
			$radius = (($max_value - $value) + .5)*100;
		} else {
			$radius = (log($max_value+1) - log($value+1) +.5)*100;
		}
		my $size = int((MAX_SIZE-3)* (log($value+1)/log($max_value+1)) )+3;

		my $x = $radius * cos ($angle);
		unless (defined $min_x) {
			$min_x = $x;
			$max_x = $size + $x;
		} elsif ($x < $min_x) {
			$min_x = $x;
		} elsif ($x+$size > $max_x) {
			$max_x = $x+$size;
		}
		my $y = $radius * sin ($angle);
		unless (defined $min_y) {
			$min_y = $y;
			$max_x = $size + $x;
		} elsif ($y < $min_y) {
			$min_y = $y;
		} elsif ($y+$size > $max_y) {
			$max_y = $y+$size;
		}

		$as2rec{$as}{x} = $x;
		$as2rec{$as}{y} = $y;
		$as2rec{$as}{size} = $size;
		$as2rec{$as}{color} = Value2Color($value/$max_value);
	}

	$min_x += $min_x*.05;
	$min_y += $min_y*.05;
	foreach my $as (keys %nodes) {
		$as2rec{$as}{x} -= $min_x;
		$as2rec{$as}{y} -= $min_y;
	}
	$max_x -= $min_x;
	$max_y -= $min_y;
	$min_x = $min_y = 0;

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
	return ($min_x, $min_y, $max_x, $max_y, $max_value);
}

########################################################################

sub Value2Color {
	my ($input) = @_;
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
		$sat = 0;100*$temp;
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
########################################################################


sub LoadData {
	my ($filename) = @_;
	open (IN, "<$filename") || die("Unable to open `$filename':$!");
	my %missing;

	my $num;
	my $line = 0;
	while (<IN>) {
		$line++;
		s/#.*//g; #Replace comment lines with a blank line
		next unless (/[^\s]/); #Skip this line if it's blank
		#last if ($num++ > 2);
		chop;

		my ($mode, @values) = split /\|/;

		if ($mode eq "d") { #If the line is for the degree of an AS
			my ($as, $transit_degree, $global_degree, $in_degree, $out_degree) = @values;

			if (defined($as && $transit_degree)) {
				if (defined($transit_degree)){
					$as2rec{$as}{"transitdegree"} = $transit_degree;
				}
				if (defined($global_degree)){
					$as2rec{$as}{"gloabldegree"} = $global_degree;
				}
				if (defined($in_degree)){
					$as2rec{$as}{"indegree"} = $in_degree;
				}
				if (defined($out_degree)){
					$as2rec{$as}{"outdegree"} = $out_degree;
				}
			}
		} elsif ($mode eq "l") { #The line is a links line
			my ($from, $to, @sources) = @values;

			if (defined $as2rec{$from}{has_loc} && defined $as2rec{$to}{has_loc}) {
				$nodes{$from} = 1;
				$nodes{$to} = 1;

				my $link = "$from $to";
				$link2rec{$link}{from} = $from;
				$link2rec{$link}{to} = $to;
			} else {
				if (!defined $as2rec{$from}{has_loc}) {
					$missing{$from} = 1;
				}
				if (!defined $as2rec{$to}{has_loc}) {
					$missing{$to} = 1;
				}
			}

		} else {
			print STDERR "READ ERROR: Line $line does not contain valid input.\n";
		}

		# if (/\s*([^\s]+)\s+([^\s]+)/) { #Grab the first two space separated values
		# 	my ($from, $to) = ($1, $2);
		# 	foreach my $as ($from, $to) {
		# 		if ($as =~ /\{(\d+)\}/) {
		# 			#$as = $1;
		# 		}
		# 	}
		# 	if (defined $as2rec{$from}{has_loc} && defined $as2rec{$to}{has_loc}) {
		# 		$nodes{$from} = 1;
		# 		$nodes{$to} = 1;

		# 		$as2rec{$from}{"outdegree"}++;
		# 		$as2rec{$to}{"indegree"}++;

		# 		my $link = "$from $to";
		# 		$link2rec{$link}{from} = $from;
		# 		$link2rec{$link}{to} = $to;
		# 	} else {
		# 		if (!defined $as2rec{$from}{has_loc}) {
		# 			$missing{$from} = 1;
		# 		}
		# 		if (!defined $as2rec{$to}{has_loc}) {
		# 			$missing{$to} = 1;
		# 		}
		# 	}
		# }
	}
	close IN;

	my @keys = sort {$a<=>$b;} keys %missing;
	if (defined $missing_print) {
		foreach my $key (@keys) {
			print STDERR "missing $key\n";
		}
	}

	my $num_missing = @keys;
	my $num_found = keys %nodes;
	print STDERR "ASs found: $num_found missing: $num_missing\n";

	if (0) {
		foreach my $key (@keys) {
			print "missing as: key:\"$key\" value:\"$missing{$key}\"\n";
		}
	}

}

sub LoadRank {
	my ($filename) = @_;
	open (IN, "<$filename") || die("Unable to open `$filename':$!");
	while(<IN>) {
		s/#.*//g;
		next unless (/[^\s]/);
		chop;
		s/,//g;
		my ($rank, $as, $name, $country, $s24, $prefix, $as_count, $degree)
			= split /\t/;
		my @values = ($rank, $name, $country, $s24, $prefix, $as_count, $degree);
		my @types = qw(rank name country count_24 count_prefix count_as
			count_degree );
		foreach my $i (0..$#types) {
			$as2rec{$as}{$types[$i]} = $values[$i]
		}
	}
	close IN;
}

sub LoadName {
	my ($filename) = @_;
	open (IN, "<$filename") || die("Unable to open `$filename':$!");
	while(<IN>) {
		s/#.*//g;
		next unless (/[^\s]/);
		chop;
		my ($as, $name) = split /\|/;
		$as2rec{$as}{name} = $name;
	}
	close IN;
}

sub LoadAsInfo {
	my ($filename) = @_;
	open (IN, "<$filename") || die("Unable to open `$filename':$!");
	while(<IN>) {
		s/#.*//g;
		next unless (/[^\s]/);
		chop;
		my ($as, $source, $name, $country, $org_name, $date) = split /\t/;
		$as2rec{$as}{name} = $org_name;
	}
	close IN;
}

sub LoadLoc {
	my ($filename) = @_;
	open (IN, "<$filename") || die("Unable to open `$filename':$!");
	my @names = qw(CONTINENT COUNTRY STATE CITY LAT LONG PREFIX_COUNT);
	while (<IN>) {
		s/#.*//g;
		next unless (/[^\s]/);
		my ($as, @values) = split /\t/;
		my ($cont, $country, $state, $city, $lat, $long) = @values;
		if (/^([^\s]+).*([-\d\.]+)\s+([-\d\.]+)\s+(\d+)$/) {
			$as2rec{$1}{LAT} = $2;
			$as2rec{$1}{LONG} = $3;
			$as2rec{$1}{PREFIX_COUNT} = $4;
			$as2rec{$1}{has_loc} = 1;
		}
	}
	close IN;

	foreach my $as (keys %as2rec) {
	if ($as =~ /_/) {
		my %copy = %{$as2rec{$as}};
		foreach my $a (split /_/) {
			unless (defined $as2rec{$a}) {
				$as2rec{$a} = \%copy;
			}
		}
	}
	
	}
}

sub PrintHeader {
	my ($min_x, $min_y, $max_x, $max_y) = @_;
	$max_x =~ s/\.\d+//g;
	$max_y =~ s/\.\d+//g;
	my $width = 500;
	my $height = 500;
	my $scale = $width/($max_x-$min_x);
	my $width_string = $max_x."pt";
	my $height_string = $max_y."pt";
	print <<EOP;
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
	xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1"
	width="$width_string" height="$height_string" viewbox="0 0 $max_x $max_y">

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
#<g transform="scale($scale)">
#</g>
}

sub PrintEnder() {
	print <<EOP;
</svg>
EOP
}
