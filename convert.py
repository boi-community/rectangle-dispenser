# Converts from the old Rectangle Dispenser text files into the new database.
# This was a very quickly hacked together script. It does its purpose, it will (ideally) only be used once.
# I've only uploaded this for posterity.

import sqlite3
import os
import sys

conn = sqlite3.connect("rectangle-dispenser.db")
cursor = conn.cursor()

with open(sys.argv[1]) as old_data:  # Play Inscryption
    cursor.execute(f'CREATE TABLE {sys.argv[2]} {("trigger", "image", "response")}')

    for line in old_data.readlines():
        line = line.strip().split("~")
        trigger = line[0]
        image = None
        response = line[1]
        if "https" in response and "png" in response:
            image = "https://" + response.split("https://")[1].rstrip()
            response = response.split("https://")[0].rstrip()

        print(f"Inserting trigger {trigger}, image {image} and response {response}")

        test = "(?,?,?)"
        # cursor.execute(f"INSERT INTO {sys.argv[2]} VALUES (?,?,?)", (trigger, image, response))
        cursor.execute(
            f"INSERT INTO {sys.argv[2]} VALUES {test}", (trigger, image, response)
        )
    conn.commit()
