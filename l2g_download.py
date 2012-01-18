#! /usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 - dasjoe   mail+git@dasjoe.de
#
# Licensed under GPL Version 3 or later

from collections import namedtuple
import os
import urllib
import re
import argparse
import sys
import subprocess
import math
from xml.dom.minidom import parse

class l2gURLopener(urllib.FancyURLopener):
	version = "Mozilla 5.0"

def findInPath(prog):
	paths = os.environ["PATH"].split(os.pathsep)
	for path in paths:
		exe_file = os.path.join(path, prog)
		if os.path.exists(exe_file) and os.access(exe_file, os.X_OK):
			return exe_file
	raise RuntimeError("Could not find %s, please install in path %s" %
	                    (prog, paths))

class Video(namedtuple('Video', 'url, name, page')):
    
    def guess_proper_downloader(self, url=None):
        url = url or self.url
        if not url: raise AttributeError('url not defined in %s' % str(self))
        if url.endswith('.mp4'):
            downloader = WgetDownloader
        elif url.startswith('rtmp://'):
            downloader = RTMPDownloader
        else:
            raise RuntimeError('Could not find appropriate downloader for %s', url)
        
        return downloader
    
    @property
    def download(self, downloader=None, target=None):
        if not downloader:
            downloader = self.guess_proper_downloader(self.url)
        return downloader(url=self.url, target=target)

class IDownloader(dict):
    '''Interface for a downloader class'''
    
    @property
    def command(self):
        attr = 'command_formatter'
        formatter = getattr(self, attr, None) or self[attr]
        assert isinstance(formatter, list)
        command = [s % self for s in formatter]
        return command
    
    def download(self):
        subprocess.Popen(self.command, shell=False).wait()
        return
        
class WgetDownloader(IDownloader):
    @property
    def command_formatter(self):
        fmt = "wget --continue".split()
        if self.get('target', None):
            fmt += ["-O", "%(target)s"]
        fmt += ["%(url)s",]
        return fmt

class RTMPDownloader(IDownloader):
    @property
    def command_formatter(self):
        fmt = "rtmpdump --resume --rtmp".split()
        fmt += ["%(url)s",]
        fmt += ["-e", "-o", "%(target)s"]
        return fmt
        
def main():
	parser = argparse.ArgumentParser(description='Download lectures from lecture2go')
	parser.add_argument('url', help="URL to the lecture's video feed")
	parser.add_argument('-l', '--list-cmd', action='store_true', help='Prints list of commands to fetch videos without actually downloading')
	parser.add_argument('-n', '--number', action='store_true', help='Name downloaded files in chronological order')
	parser.add_argument('-c', '--cwd', help='Change working directory')
	args = parser.parse_args()

	if args.url[-8:] != ".mp4.xml":
		sys.exit("ERROR: URL is not a video feed")

	list_cmd = False
	if args.list_cmd:
		list_cmd = True

	number_files = False
	if args.number:
		number_files = True

	curdir = os.path.abspath(os.curdir)
	if args.cwd:
	    os.chdir(args.cwd)
	
	loader = l2gURLopener()
	#feed = loader.open(args.url).read()
	feed = loader.open(args.url)

	dom = parse(feed)

	videos = []

	for item in dom.getElementsByTagName("item"):
		videoName = item.getElementsByTagName("title").item(0).firstChild.nodeValue
		videoPage = item.getElementsByTagName("link").item(0).firstChild.nodeValue
		enclosure = item.getElementsByTagName("enclosure").item(0)
		if enclosure:
		    videoURL = enclosure.getAttribute('url')
		else:
		    videoURL = None
		    # We skip items that are not downloadable
		    continue
		video = Video(name=videoName, url=videoURL, page=videoPage)
		videos.append(video)

	videos.sort()

	downloads = [v.download for v in videos]
	padding = int(math.log10(len(videos)))+1

	for number, download in enumerate(downloads):
		num = ""
		if (number_files):
			num = "%0*d-"%(padding, number)
		if list_cmd:
			print ' '.join(download.command)
		else:
			print "Getting %s " % download
			download.download()

	os.chdir(curdir)

if __name__ == "__main__":
	main()
