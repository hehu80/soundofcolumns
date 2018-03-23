#MIT License
#
#Copyright (c) 2018, Henning Voss <henning@huhehu.com>
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.

__author__="Henning Voss <henning@huhehu.com>"
__date__ ="$02.01.2018 17:56:38$"

import requests 
import time
import urllib2
import csv
import argparse
import codecs
import cStringIO
import os

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


def download_sound(url, sound, target):
    sound = sound.replace("/", "_")
    sound = sound.replace(".", "_")
    sound = sound.replace("?", "_")
    sound = sound.replace("!", "_")
    sound = sound.replace(" ", "")
    sound = sound.replace("__", "_")
    sound = sound + '.mp3'

    file = urllib2.urlopen(url)
    with open(target + '/' + sound,'wb') as output:
        output.write(file.read())

    return sound


def get_sound_id(sound, language):
    headers = {'Content-type': 'application/json'}

    sound = sound.replace("/", " ")
    sound = sound.replace("  ", " ")

    url = "https://api.soundoftext.com/sounds"
    payload = {'engine': 'Google', 'data': {'text': sound, 'voice': language}}
    request = requests.post(url, json=payload, headers=headers)   

    while True:
        url = "https://api.soundoftext.com/sounds/" + request.json()['id'] 
        request = requests.get(url, headers=headers)
        if request.json()['status'] == 'Done':  
            return request.json()['location']
        else:
            time.sleep(1)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='A simple script to download sound files from www.soundoftext.com.', epilog='')

    parser.add_argument('source', help='source CSV file containing all the texts you want to download')
    parser.add_argument('--target', '-t', help='target CSV file, empty to save result in same CSV file', default=(''), dest='target')
    parser.add_argument('--firstrow', '-f', help='first row in CSV file', default=(1), type=int, dest='first_row')
    parser.add_argument('--column', '-c', help='column in source CSV file containing all the texts you want to download', default=(1), type=int, dest='column')
    parser.add_argument('--soundcolumn', '-s', help='column for sound file name in target CSV file', default=(0), type=int, dest='sound_column')
    parser.add_argument('--directory', '-d', help='target directory for sound files', default=('.'), dest='directory')
    parser.add_argument('--language', '-l', help='language code (https://soundoftext.com/docs#voices)', default=('cmn-Hant-TW'), dest='language')
    parser.add_argument('--soundformat', '-sf', help='format for sound column, e.g. \"A{0}B\" while {0} is the name of the sound file', default=(u'[sound:{0}]'), dest='sound_format')

    args = parser.parse_args()
    
    if args.first_row <= 0:
        parser.error("please choose a valid number for the first row")
    if args.column <= 0:
        parser.error("please choose a valid column number")
    if args.column == args.sound_column:
        parser.error("please choose a different column number for the sound file")
    if args.target == '':
            args.target = args.source
            
    source_file = open(args.source)
    target_file = open(args.target + ".2.csv", 'wb')
    reader = UnicodeReader(source_file)
    writer = UnicodeWriter(target_file)
    
    for row in reader:
        args.first_row = args.first_row - 1
        if (args.first_row <= 0) and (len(row) > args.column):
            sound = row[args.column - 1]
            if (sound != '') and (args.sound_column <= 0 or len(row) < args.sound_column or row[args.sound_column - 1] == ''):
                print "download sound " + sound
                try:
                    sound_file = download_sound(get_sound_id(sound, args.language), sound, args.directory)
                    if (args.sound_column > 0):
                        while len(row) < args.sound_column:
                            row.append('')
                    row[args.sound_column - 1] = args.sound_format.format(sound_file)
                except:
                    print "download failed"
        writer.writerow(row)

    source_file.close()
    target_file.close() 
    
    os.rename(args.target + ".2.csv", args.target)
            
