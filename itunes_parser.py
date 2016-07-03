from xml.etree import ElementTree
import json
import os

#replace %20 with space and remove "file://localhost/" prefix
def sanitize_file_location(location):
	location = location.replace("%20", " ")
	location = strip_prefix(location, "file://localhost/")
	return location

def strip_prefix(str, prefix):
	if (str.startswith(prefix)):
		str = str[len(prefix):]
	return str

#Takes the list of tags contained in each track's <dict> tag and parses them to a Python dictionary with only the fields we're interested in
def parse_track_data_to_dict(track_data):
	#initialize variables
	artist = None
	album = None
	name = None
	track_number = None
	location = None
	#iterate list of tags
	for i in range(0, len(track_data)):
		field = track_data[i]
		#if the tag is one of the keys that we're interested in, get the value of the next tag in the list
		if field.tag == "key" and field.text == "Name":
			name = track_data[i+1].text
		if field.tag == "key" and field.text == "Artist":
			artist = track_data[i+1].text
		if field.tag == "key" and field.text == "Album":
			album = track_data[i+1].text
		if field.tag == "key" and field.text == "Track Number":
			track_number = track_data[i+1].text																
		if field.tag == "key" and field.text == "Location":
			location = track_data[i+1].text
			location = sanitize_file_location(location)
	track_data_dict = {
		"name": name,
		"artist": artist,
		"album": album,
		"track_number": track_number,
		"location": location
	}
	return track_data_dict

#Takes the root of the XML tree for the iTunes library file and parses it to a dictionary indexed by track ID
def parse_library_xml_to_dict(root):
	tracks_xml = root.find("dict").find("dict")
	tracks_dict = dict()
	counter = 0
	for element in tracks_xml:
		#tags are expected to alternate between <key> and <dict> containing the track data
		if counter % 2 is 0:
			#extra safety check that this is the <key> tag
			if element.tag == "key":
				key = element.text
			else:
				raise ValueError("unexpected tag")
		else:
			#extra safety check that this is the <dict> tag
			if element.tag == "dict":
				#parse track data to Python dictionary and add to overall tracks dictionary
				track_data_dict = parse_track_data_to_dict(list(element))
				tracks_dict[key] = track_data_dict
			else:
				raise ValueError("unexpected tag")
		counter += 1
	return tracks_dict	

itunes_install_dir = os.path.normpath("")
library_file = os.path.join(itunes_install_dir, "iTunes Music Library.xml")
library_base_dir = os.path.join(itunes_install_dir, "iTunes Music")

root = ElementTree.parse(library_file).getroot()
tracks_dict = parse_library_xml_to_dict(root)