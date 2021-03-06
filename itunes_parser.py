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

#translates iTunes' "Kind" field to smaller subset of values
def kind_to_file_type(kind):
	if "audio" in kind:
		return "audio"
	elif "video" in kind or "movie" in kind:
		return "video"
	elif "game" in kind:
		return "game"
	else:
		return "unknown"

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
		if field.tag == "key" and field.text == "Kind":
			kind = track_data[i+1].text
			file_type = kind_to_file_type(kind)
		if field.tag == "key" and field.text == "Location":
			location = track_data[i+1].text
			location = sanitize_file_location(location)
	track_data_dict = {
		"name": name,
		"artist": artist,
		"album": album,
		"track_number": track_number,
		"location": location,
		"file_type": file_type
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

def parse_playlist_xml_to_dict(playlist_xml, tracks_dict, library_base_dir):
	tracks = list()
	#for subelement in playlist_xml:
	for i in range(0, len(playlist_xml)):
		field = playlist_xml[i]
		#if the tag is one of the keys that we're interested in, get the value of the next tag in the list
		if field.tag == "key" and field.text == "Name":
			name = playlist_xml[i+1].text
		if field.tag == "key" and field.text == "Playlist Items":
			#get list of playlist items and iterate
			playlist_items_xml = list(playlist_xml[i+1])
			for playlist_item in playlist_items_xml:
				#track ID will always be the text of the second tag in the playlist <dict> entry
				track_id = list(playlist_item)[1].text
				track = tracks_dict[track_id]
				relative_file_path = get_target_relative_file_path(track, library_base_dir)
				tracks.append(relative_file_path)

	return {
		"name": name,
		"tracks": tracks
	}

def parse_playlists(root, tracks_dict, library_base_dir):
	playlists_xml = root.find("dict").find("array")
	blacklist = [
		"####!####",
		"Apps",
		"Genius",
		"iTunes U",
		"Music",
		"PDFs",
		"Rentals"
	]
	playlists = list()
	for element in playlists_xml:
		playlist_xml = list(element)
		playlist = parse_playlist_xml_to_dict(playlist_xml, tracks_dict, library_base_dir)
		if playlist["name"] not in blacklist:
			playlists.append(playlist)
	return playlists

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
	return str.strip()

def copy_file(source, dest):
	if not os.path.exists(os.path.split(dest)[0]):
		os.makedirs(dest)
	shutil.copyfile(source, dest)

def print_str(str):
	try:
		print(str)
	except Exception as e:
		print(str.encode("utf-8"))

def get_target_relative_file_path(track, library_base_dir):
	location = track['location']
	if location is not None:
		if location.startswith(library_base_dir):
			relative_path = strip_prefix(location, library_base_dir)
		else:
			filename = os.path.split(location)[1]
			extension = os.path.splitext(filename)[1]
			if track['artist'] is not None and track['album'] is not None:
				relative_path = os.path.join(
					escape_unsafe_filename_characters(track['artist']),
					escape_unsafe_filename_characters(track['album']),
					escape_unsafe_filename_characters(track['name']) + extension
				)
			elif track['artist'] is not None:
				relative_path = os.path.join(
					escape_unsafe_filename_characters(track['artist']),
					escape_unsafe_filename_characters(track['name']) + extension
				)
			else:
				relative_path = filename
		return relative_path

def get_list_of_files_to_copy(dest_base_dir, library_base_dir, tracks_dict):
	files_to_copy_list = list()
	for key, track in tracks_dict.items():
		relative_path = get_target_relative_file_path(track, library_base_dir)
		if relative_path is not None:
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

def copy_playlists(playlists, dest_base_dir):
	if not os.path.exists(dest_base_dir):
		os.makedirs(dest_base_dir)
	for playlist in playlists:
		filename = os.path.join(dest_base_dir, escape_unsafe_filename_characters(playlist["name"])) + ".m3u"
		output_file = open(filename, "w")
		for track in playlist["tracks"]:
			if track is not None:
				output_file.write(track + "\n")
		output_file.close()

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

playlists = parse_playlists(root, tracks_dict, library_base_dir)
copy_playlists(playlists, dest_base_dir)