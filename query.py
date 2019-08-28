import sqlite3
from sqlite3 import Error
import json, sys, os

path = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(path, "config.json")) as config_file:
    config = json.load(config_file)
    dbFolder = config.get("db_folder")
    filename = os.path.join (dbFolder, "USPSTracking.db")

connection = sqlite3.connect (filename)
cur = connection.cursor ()
cur.execute ("SELECT * FROM trackings")
results = cur.fetchall ()

for result in results:
    if 'PHILADELPHIA' in result[2] \
        and 'July' not in result[2] \
        and 'FRANCE' in result[2]:
        print (result, "\r\n")

