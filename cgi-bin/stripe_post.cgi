#!/usr/bin/perl
use strict;
use warnings FATAL => 'all';

use CGI::Carp qw/fatalsToBrowser/; # recommended to handle any errors, but can be removed if you prefer ro
use MIME::Base64;
use LWP::UserAgent;
use HTTP::Request::Common;
use JSON::XS;

# use Data::Dumper;

################## USER VARS SETUP
# Your actual API key (take one here, please: https://stripe.com/docs/keys).
my $SECRET_API_KEY = 'sk_test_51KokjQL60rUiNeHv9W0yOLfp1HpPz1zKirYm6RTD3CHMC20BYLWkShy5OkA1TIfVtjCYZ6C47rwnOZ0jR1TviaOs00TJCLVVXA:';

# The URI for the API. Do not change unless you know what you do.
my $host = 'https://api.stripe.com/v1/checkout/sessions';

# two addresses below do not have to manage any data form Stripe, but are just static,
# because Stripe will NOT send ANY information to those pages. Only redirects.
my $success_url = "https://example.com/success.html"; # full page address when a payment is SUCCESSFUL
my $cancel_url = "https://example.com/cancel.html"; # full page address when a payment is FAILED

# a filename for storing vital payment data. You will need to use RDBS instead.
my $new_payment_file = "sent_payment_data.csv";
#############################

=head2 Query
	Reading the query from the "Buy Now" link on your online store.
	It accepts:
		user_id = TEXT (mandatory),
		price = INT (in cents, but not less than 50 cents) (mandatory),
		prod_name = TEXT (optional) - product name,
		prod_descr = TEXT (optional) - product description
		Here is a link example:
		<a href="https://example.com/cgi-bin/stripe_post.cgi?user_id=testUserId_015883&price=7050&prod_name=Test Product name&prod_descr=Descriptiont for this product" title="Link example">Test Product name</a>
=cut

my %QUERY_hash;
if ($ENV{'QUERY_STRING'} && length ($ENV{'QUERY_STRING'}) > 0){
	my $buffer = $ENV{'QUERY_STRING'};
	my @_qPairs = split(/&/, $buffer);
	foreach (@_qPairs){
		my ($_key, $_value) = split(/=/, $_);
		$_value =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
		$QUERY_hash{$_key} = $_value;
	}
	if (!$QUERY_hash{'price'} || $QUERY_hash{'price'} =~/\D/g) {
		die "Please, check the query. It does not meet minimum demands (no/incorrect price field)"
	}
	elsif (!$QUERY_hash{'user_id'} || $QUERY_hash{'user_id'} =~/\W/g) {
		die "Please, check the query. It does not meet minimum demands (no/incorrect user_id field)"
	}
	
	# cleaning up the rest (optional) data
	$QUERY_hash{'prod_name'} =~ s/["\(\)\[\],:; ]//g; # or, alternatively, you can use just \W class.
	$QUERY_hash{'prod_descr'} =~ s/["\(\)\[\],:; ]//g; # or, alternatively, you can use just \W class.
	
} # if $ENV{'QUERY_STRING'}

else {
	die "Pardon, no parameters have been given..";
}

# Creating an LWP object and setting it up
my $ua = LWP::UserAgent->new();
$ua->agent('Mozilla/4.76 [en] (Win98; U)'); # can be changed if needed
$ua->default_header('Authorization',  "Basic " . MIME::Base64::encode($SECRET_API_KEY, ''));
$ua->default_header('Stripe_Version',  '2020-08-27'); # Stripe API ver. Do not change it, unless you know what you do

# the constructor below represents ths settings for a one product sale, "baked" on fly
my $response = $ua->request(POST $host,
	[
		'success_url'              => $success_url,
		'cancel_url'               => $cancel_url,
		'mode'                     => 'payment', # do not change
		'client_reference_id'      => $QUERY_hash{user_id}, # any pattern within regex \w class to identify the Customer on your side
		'submit_type'              => 'pay', # do not change unless you know what you do
		'customer_creation'        => 'if_required', # do not change unless you know what you do
		'line_items[0][price_data][currency]'                   => 'usd',
		'line_items[0][quantity]'                               => 1, # a number of items of this type sold altogether
		'line_items[0][price_data][product_data][name]'         => $QUERY_hash{prod_name} || 'Product purchase', # the current item's name
		'line_items[0][price_data][product_data][description]'  => $QUERY_hash{prod_descr} || 'No description', # the current item's description (optional)
		'line_items[0][price_data][unit_amount]'                => $QUERY_hash{price}, # the product's price IN THE CENTS (5000 is for 50 USD)
	]
);

if ($response->is_success) {
	
	# decoding JSON data from Stripe with the session information and storing it into a CSV file (you will use RDBS instead)
	my $href_from_json  = decode_json $response->decoded_content;
	
	# checking if the data structure is legal for Stripe obj API ver. 2020-08-27
	if (
	
	###############################################################
	################
	# сравнить полученные данные с теми, что мы ТОПРАВИЛИ выше (+ структурные элементы общие для этого объекта Stripe)
		$href_from_json->{object} and $href_from_json->{object} eq "event"
		and $href_from_json->{id} and $href_from_json->{id} =~/^\w+$/
		and $href_from_json->{api_version} and $href_from_json->{api_version} eq '2020-08-27'
		and $href_from_json->{type} and $href_from_json->{type} eq 'checkout.session.completed'
		and $href_from_json->{data}->{object}->{id} and $href_from_json->{data}->{object}->{id} =~/^\w+$/
		and $href_from_json->{data}->{object}->{object} and $href_from_json->{data}->{object}->{object} eq 'checkout.session'
		and $href_from_json->{data}->{object}->{customer_details}->{email} and $href_from_json->{data}->{object}->{customer_details}->{email} =~/[\w\@]+/
		and $href_from_json->{data}->{object}->{customer_details}->{name} and $href_from_json->{data}->{object}->{customer_details}->{name} =~/\w+/
	) {
		
		# cleaning up the data from the unsafe symbols
		$href_from_json->{data}->{object}->{client_reference_id} =~ s/["\(\)\[\],:; ]//g; # or, alternatively, you can use just \W class.
		$href_from_json->{data}->{object}->{amount_total} =~ s/\D//g;
		$href_from_json->{data}->{object}->{id} =~ s/\W//g;                                     # do NOT change it, please.
		$href_from_json->{data}->{object}->{customer_details}->{email} =~ s/["\(\)\[\],:; ]//g; # do NOT change it, please.
		$href_from_json->{data}->{object}->{customer_details}->{name} =~ s/[^\w \'\-]//g; # do NOT change it, please.
		
		open (STORAGE, "> $new_payment_file") or die "Could not manage to open the $new_payment_file for writing. Please, check the permissions.";
		# we store: [user_id], [amount] and [SSID] to help you pick the right session from your RDBS on the payment completion.
		print STORAGE <<CSV;
	user_id, $href_from_json->{client_reference_id}
	amount, $href_from_json->{amount_total}
	SSID, $href_from_json->{id}
CSV
		close STORAGE;
		
		# redirecting to the payment page at Stripe.com for this session
		print "Location: $href_from_json->{url}\n\n";
		exit;
	}
	else {
		print "Content-type: text/plain", "\n";
		print "Status: 400 Bad Request", "\n\n";
		print "Invalid data!\n";
	}
	
}
else {
	die 'Stripe returned an error: "'.$response->status_line."\"\n"; # can be replaced with a custom error page. The error can be stored in the log, if needed.
}
