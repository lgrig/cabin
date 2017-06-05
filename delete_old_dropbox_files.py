import json
import dropbox
import os
import datetime

class DeleteFromDropbox():
    def __init__(self):
        self.dbx = dropbox.Dropbox(json.load(open(os.path.dirname(os.path.realpath(__file__)) + '/.config.json'))['dropbox']['token'])
        self.dropbox_file_path = "/photos/"

    def get_dropbox_entries(self):
        entries = [{'id': entry.id, 'name': entry.name, 'last_modified': entry.server_modified} for entry in self.dbx.files_list_folder(self.dropbox_file_path).entries]
        old_entries = [entry['id'] for entry in entries if entry['server_modified'] < datetime.datetime.now() + datetime.timedelta(-30)]
        response = dbx.files_delete_batch_check(dbx.files_delete_batch(old_entries))
        print(response)
