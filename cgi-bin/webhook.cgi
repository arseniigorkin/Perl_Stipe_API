#!/usr/bin/perl
use strict;
use warnings FATAL => 'all';
use JSON::XS;
use CGI::Carp qw /fatalsToBrowser/;
# use Data::Dumper;

################## USER VARS SETUP
# a filename for storing vital payment data. You will need to use RDBS instead.
my $completed_payment_file = "completed_payment_data.csv";
#############################

# reading from the STDIN (REST)
my $response;
while(<>) {
	$_ =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
	$response .= $_;
}

if ($response) {
	# decoding JSON into href
	my $href_from_json = decode_json $response;
	
	# checking if the data structure is legal for Stripe obj API ver. 2020-08-27
	if (
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
		
		# writing the data into the file (CSV format). Here you should use your RDBS instead.
		open(FILE, "> $completed_payment_file") or die "Could not cope with opening the $completed_payment_file. Please, check the permissions.";
		# we store: [user_id], [amount], [customer's email] and [SSID] to help you pick the right session from your RDBS.
		print FILE <<CSV;
user_id, $href_from_json->{data}->{object}->{client_reference_id}
amount, $href_from_json->{data}->{object}->{amount_total}
SSID, $href_from_json->{data}->{object}->{id}
email, $href_from_json->{data}->{object}->{customer_details}->{email}
name, $href_from_json->{data}->{object}->{customer_details}->{name}
CSV
		
		close FILE;
		
		print "Content-type: text/plain\n";
		print "Status: 200 OK\n\n";
		print "Payment is successful!\n";
	} # JSON checks (IF)
	
	else {
		print "Content-type: text/plain", "\n";
		print "Status: 400 Bad Request", "\n\n";
		print "Invalid data!\n";
	}
} # if response

else {
	print "Content-type: text/plain", "\n";
	print "Status: 400 Bad Request", "\n\n";
	print "No data given!\n";
}
