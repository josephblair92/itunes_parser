from xml.etree import ElementTree
import json
import os
import argparse
import urllib.parse
import shutil

#replace %20 with space and remove "file://localhost/" prefix
def sanitize_file_location(location):
	location = urllib.parse.unquote(location)
	location = strip_prefix(location, "file://localhost/")
	location = os.path.normpath(location)
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

def escape_unsafe_filename_characters(str):
	str = str.replace("<","_") \
	.replace(">","_") \
	.replace(":","_") \
	.replace("\"","_") \
	.replace("/","_") \
	.replace("\\","_") \
	.replace("|","_") \
	.replace("?","_") \
	.replace("*","_") 
	return str

def copy_file(source, dest):
	if not os.exists(os.path.split(dest)[0]):
		os.makedirs(dest)
	shutil.copyfile(source, dest)

def print_str(str):
	try:
		print(str)
	except Exception as e:
		print(str.encode("utf-8"))

def get_list_of_files_to_copy(dest_base_dir, library_base_dir, tracks_dict):
	files_to_copy_list = list()
	for key, track in tracks_dict.items():
		location = track['location']
		if location is not None:
			if location.startswith(library_base_dir):
				relative_path = strip_prefix(location, library_base_dir)
			else:
				filename = os.path.split(location)[1]
				if track['artist'] is not None and track['album'] is not None:
					relative_path = os.path.join(
						escape_unsafe_filename_characters(track['artist']),
						escape_unsafe_filename_characters(track['album']),
						escape_unsafe_filename_characters(track['name'])
					)
				elif track['artist'] is not None:
					relative_path = os.path.join(
						escape_unsafe_filename_characters(track['artist']),
						escape_unsafe_filename_characters(track['name'])
					)
				else:
					relative_path = filename
			dest_path = os.path.join(dest_base_dir, relative_path)
			files_to_copy_list.append((track['location'], dest_path))
	return files_to_copy_list

def copy_library(dest_base_dir, library_base_dir, tracks_dict):
	files_to_copy_list = get_list_of_files_to_copy(dest_base_dir, library_base_dir, tracks_dict)
	total_files = len(files_to_copy_list)
	counter = 1
	for file in files_to_copy_list:
		print_str("Copying " + file[0] + " to " + file[1] + " (" + str(counter) + "/" + str(total_files) + ")")
		counter += 1
		#copy_file(file[0], file[1])

parser = argparse.ArgumentParser()
parser.add_argument('--itunes-base-dir', type=str, dest="itunes_base_dir",
						help='Base directory of iTunes library.')
parser.add_argument('--dest-base-dir', type=str, dest="dest_base_dir",
						help='Base directory of iTunes library.')
args = parser.parse_args()

itunes_base_dir = os.path.normpath(args.itunes_base_dir)
library_file = os.path.join(itunes_base_dir, "iTunes Music Library.xml")
library_base_dir = os.path.join(itunes_base_dir, "iTunes Music", "")

root = ElementTree.parse(library_file).getroot()
tracks_dict = parse_library_xml_to_dict(root)

dest_base_dir = os.path.normpath(args.dest_base_dir)
copy_library(dest_base_dir, library_base_dir, tracks_dict)	