#!/usr/bin/env python
'''
Copyright (c) 2012 David Drake

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


nasa_apod_desktop.py
https://github.com/randomdrake/nasa-apod-desktop

Written/Modified by David Drake
http://randomdrake.com
http://twitter.com/randomdrake

Based on apodbackground: http://sourceforge.net/projects/apodbackground/
Which, is based on: http://0chris.com/nasa-image-day-script-python.html
-Removed adding text
-Resizing without scaling and adding black background
-Cleaned up code and comments
-Added debug lines
-Check to see if file already exists before attempting download
-Saving as PNG instead of JPG for improved quality


Tested on Ubuntu 12.04


DESCRIPTION
1) Grabs the latest image of the day from NASA (http://apod.nasa.gov/apod/).
2) Resizes the image to the given resolution.
3) Sets the image as your desktop.
4) Adds the image to a list of images that will be cycled through.


INSTALLATION
Ensure you have Python installed (default for Ubuntu) and the python-imaging package:
sudo apt-get install python-imaging

Set your resolution variables and your download path (make sure it's writeable):
'''
DOWNLOAD_PATH = '/home/nic/backgrounds/'
DESKTOP_PATH = '/home/nic/Desktop/'
RESOLUTION_X = 1920
RESOLUTION_Y = 2160
MULTI_SCREEN = True
'''

RUN AT STARTUP
To have this run whenever you startup your computer, perform the following steps:
1) Click on the settings button (cog in top right)
2) Select "Startup Applications..."
3) Click the "Add" button
4) Enter the following:
Name: NASA APOD Desktop
Command: python /path/to/nasa_apod_desktop.py
Comment: Downloads the latest NASA APOD and sets it as the background.
5) Click on the "Add" button
'''
import commands
import urllib
import urllib2
import re
import os
import pickle
from PIL import Image
from sys import stdout, argv

try:
    import pygtk
    pygtk.require('2.0')
    import pynotify
except:
    pass

# Configurable settings:
NASA_APOD_SITE = 'http://apod.nasa.gov/apod/'
SHOW_DEBUG = True
PICKLE_FILE = os.path.join(DOWNLOAD_PATH, "history.pickle")
HISTORY_DATA = {'history': [], 'current': None}


def download_site(url):
    ''' Download HTML of the site'''
    if SHOW_DEBUG:
        print "Downloading contents of the site to find the image name"
    opener = urllib2.build_opener()
    req = urllib2.Request(url)
    response = opener.open(req)
    reply = response.read()
    return reply


def get_image_url(text):
    ''' Finds the image URL '''
    if SHOW_DEBUG:
        print "Grabbing the image URL"
    reg = re.search('<a href="(image.*?)"', text, re.DOTALL)
    if 'http' in reg.group(1):
        # Actual url
        file_url = reg.group(1)
    else:
        # Relative path, handle it
        file_url = NASA_APOD_SITE + reg.group(1)
    return file_url


def get_image(file_url):
    ''' Saves image at URL '''
    filename = os.path.basename(file_url)
    save_to = DOWNLOAD_PATH + os.path.splitext(filename)[0] + '.png'
    if not os.path.isfile(save_to):
        if SHOW_DEBUG:
            print "Opening remote URL"
        remote_file = urllib.urlopen(file_url)

        if SHOW_DEBUG:
            file_size = float(remote_file.headers.get("content-length"))
            print "Retrieving image"
            urllib.urlretrieve(file_url, save_to, print_download_status)

            # Adding additional padding to ensure entire line
            if SHOW_DEBUG:
                print "\rDone downloading", human_readable_size(file_size), "       "
        else:
            urllib.urlretrieve(file_url, save_to)
    elif SHOW_DEBUG:
        print "File exists, moving on"

    return save_to


def get_title(text):
    if SHOW_DEBUG:
        print "grabbing title"
    reg = re.search('<img[^>]*></a>[\s]*?</center>[\s]*?<center>[\s]*?<b>[\s]*?(.*?)[\s]*?</b>', text, re.DOTALL | re.IGNORECASE)
    return reg.group(1)


def resize_image(filename):
    ''' Resizes the image to the provided dimensions '''
    if SHOW_DEBUG:
        print "Opening local image"

    image = Image.open(filename)
    if SHOW_DEBUG:
        print "Resizing the image to", RESOLUTION_X, 'x', RESOLUTION_Y
    image = image.resize((RESOLUTION_X, RESOLUTION_Y), Image.ANTIALIAS)

    if SHOW_DEBUG:
        print "Saving the image to", filename
    fhandle = open(filename, 'w')
    image.save(fhandle, 'PNG')


def set_gnome_wallpaper(file_path):
    ''' Sets the new image as the wallpaper '''
    if SHOW_DEBUG:
        print "Setting the wallpaper"
    command = "gsettings set org.gnome.desktop.background picture-uri file://" + file_path
    if MULTI_SCREEN:
        command = command + " | gsettings set org.gnome.desktop.background picture-options spanned"

    status, output = commands.getstatusoutput(command)
    return status


def print_download_status(block_count, block_size, total_size):
    written_size = human_readable_size(block_count * block_size)
    total_size = human_readable_size(total_size)

    # Adding space padding at the end to ensure we overwrite the whole line
    stdout.write("\r%s bytes of %s         " % (written_size, total_size))
    stdout.flush()


def human_readable_size(number_bytes):
    for x in ['bytes', 'KB', 'MB']:
        if number_bytes < 1024.0:
            return "%3.2f%s" % (number_bytes, x)
        number_bytes /= 1024.0


def notify_exists():
    if not pynotify.init("Basics"):
        return False
    else:
        return True


def get_previous():
    if len(HISTORY_DATA['history'][:HISTORY_DATA['current']]) > 0:
        set_gnome_wallpaper(HISTORY_DATA['history'][HISTORY_DATA['current'] - 1]['file'])
        HISTORY_DATA['current'] = HISTORY_DATA['current'] - 1
        save_data()
        return HISTORY_DATA['history'][HISTORY_DATA['current']]
    else:
        return False


def get_next():
    if len(HISTORY_DATA['history'][HISTORY_DATA['current']:]) > 1:
        set_gnome_wallpaper(HISTORY_DATA['history'][HISTORY_DATA['current'] + 1]['file'])
        HISTORY_DATA['current'] = HISTORY_DATA['current'] + 1
        save_data()
        return HISTORY_DATA['history'][HISTORY_DATA['current']]
    else:
        return False


def open_data():
    if not os.path.exists(PICKLE_FILE):
        pickle.dump(HISTORY_DATA, open(PICKLE_FILE, "wb"))

    return pickle.load(open(PICKLE_FILE, "rb"))


def save_data():
    pickle.dump(HISTORY_DATA, open(PICKLE_FILE, "wb"))


if __name__ == '__main__':
    ''' Our program '''
    if SHOW_DEBUG:
        print "Starting"

    # Check for Notify
    NOTIFY_ON = notify_exists()
    HISTORY_DATA = open_data()

    # Create the download path if it doesn't exist
    if not os.path.exists(os.path.expanduser(DOWNLOAD_PATH)):
        os.makedirs(os.path.expanduser(DOWNLOAD_PATH))

    # Grab the HTML contents of the file
    site_contents = download_site(NASA_APOD_SITE)
    image_title = get_title(site_contents)
    image_url = get_image_url(site_contents)
    if len(argv) < 2:
        if len(HISTORY_DATA['history']) < 1 or not HISTORY_DATA['history'][-1]['url'] == image_url:

            # Check for notify and send message about starting
            nasa_logo = "file://" + os.path.join(os.path.dirname(os.path.realpath(__file__)), "nasa.png")
            if NOTIFY_ON:
                n = pynotify.Notification("NASA APOD Desktop", "Fetching Astronomy Picture of the Day...", nasa_logo)
                n.show()

            # Download the image
            filename = get_image(image_url)

            # Resize the image
            resize_image(filename)

            # Set the wallpaper
            status = set_gnome_wallpaper(filename)

            # Update Hitory
            HISTORY_DATA['history'].append({'url': image_url, 'file': filename, 'title': image_title})
            HISTORY_DATA['current'] = len(HISTORY_DATA['history']) - 1
            save_data()

            # Check for notify and send message about finishing!
            if NOTIFY_ON:
                n.update("NASA APOD Desktop", "Updated Background \n\"" + image_title + "\"", filename)
                n.show()

            if SHOW_DEBUG:
                print "Finished!"
        else:
            result = HISTORY_DATA['history'][HISTORY_DATA['current']]
            set_gnome_wallpaper(result['file'])
            if result and NOTIFY_ON:
                n = pynotify.Notification("NASA APOD Desktop", "Updated Background \n\"" + result['title'] + "\"", result['file'])
                n.show()
    else:
        if argv[1] == "next":
            result = get_next()
            if result and NOTIFY_ON:
                n = pynotify.Notification("NASA APOD Desktop", "Updated Background \n\"" + result['title'] + "\"", result['file'])
                n.show()

        if argv[1] == "previous":
            result = get_previous()
            if result and NOTIFY_ON:
                n = pynotify.Notification("NASA APOD Desktop", "Updated Background \n\"" + result['title'] + "\"", result['file'])
                n.show()

        if argv[1] == "write-desktop-files":
            if not os.path.exists(os.path.join(DESKTOP_PATH, 'nasa-apod-desktop-previous.desktop')):
                with open(os.path.join(DESKTOP_PATH, 'nasa-apod-desktop-previous.desktop'), "w") as next_file:
                    next_file.write("""[Desktop Entry]
Version=1.0
Type=Application
Name=<
Exec=python """ + os.path.realpath(__file__) + """ previous
Icon=/usr/share/icons/oxygen/64x64/actions/go-previous.png
Comment=Goes to the previous background in your NASA APOD history
Categories=
MimeType=""")

            if not os.path.exists(os.path.join(DESKTOP_PATH, 'nasa-apod-desktop.desktop')):
                with open(os.path.join(DESKTOP_PATH, 'nasa-apod-desktop.desktop'), "w") as next_file:
                    next_file.write("""[Desktop Entry]
Version=1.0
Type=Application
Name=NASA APOD
Exec=python """ + os.path.realpath(__file__) + """
Icon=""" + os.path.join(os.path.dirname(os.path.realpath(__file__)), "nasa.png") + """
Comment=Checks for new NASA APOD images and set's it as your background
Categories=
MimeType=""")
            if not os.path.exists(os.path.join(DESKTOP_PATH, 'nasa-apod-desktop-next.desktop')):
                with open(os.path.join(DESKTOP_PATH, 'nasa-apod-desktop-next.desktop'), "w") as next_file:
                    next_file.write("""[Desktop Entry]
Version=1.0
Type=Application
Name=>
Exec=python """ + os.path.realpath(__file__) + """ next
Icon=/usr/share/icons/oxygen/64x64/actions/go-next.png
Comment=Goes to the next background in your NASA APOD history
Categories=
MimeType=""")
