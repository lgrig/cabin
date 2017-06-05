import json
import dropbox
import os
dbx = dropbox.Dropbox(json.load(open(os.path.dirname(os.path.realpath(__file__)) + '/.config.json'))['dropbox']['token'])
dropbox_file_path = "/photos/"
local_path = '/home/pi/development/python/cabin_camera/photos/'
for filename in  os.listdir(local_path):
    #upload the file to dropbox
    with open(local_path + filename, 'rb') as f:
        dbx.files_upload(f.read(), dropbox_file_path + filename)
    #delete the file
    os.remove(local_path + filename)
