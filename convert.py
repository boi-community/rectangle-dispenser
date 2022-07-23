# Converts from the old Rectangle Dispenser text files into the new database.
# This was a very quickly hacked together script. It does its purpose, it will (ideally) only be used once.
# I've only uploaded this for posterity.

# nvm apparently veesus intends to use this regularly :)

import sqlite3
import os
import sys

conn = sqlite3.connect("rectangle-dispenser.db")
cursor = conn.cursor()

with open(sys.argv[1]) as old_data:  # Play Inscryption
    try:
        cursor.execute(f'CREATE TABLE {sys.argv[2]} {("trigger", "image", "response")}')
    except sqlite3.OperationalError:
        pass
    old_data = old_data.readlines()
    data = []
    for i in range(len(old_data)):
        line = old_data[i].strip().replace("’", "'").split("~")
        if line[0] == "Key Terms" and sys.argv[2] == "official":
            sys.argv[
                2
            ] = "game_help"  # ugly hack because response.txt has game help *and* official in one file
            try:
                cursor.execute(
                    f'CREATE TABLE {sys.argv[2]} {("trigger", "image", "response")}'
                )
            except sqlite3.OperationalError:
                pass
        if line[0] == "Template":
            break
        if len(line) > 1:
            trigger = line[0]
            image = None
            response = line[1]
            if "https" in response and "png" in response:
                image = "https://" + response.split("https://")[1].rstrip()
                response = response.split("https://")[0].rstrip()
            data.append(
                {
                    "trigger": trigger,
                    "image": image,
                    "response": response,
                    "cardset": sys.argv[2],
                }
            )
        elif line[0]:
            # if there's stuff in the previous line, append to the last value of data
            prev_line = old_data[i - 1].strip().split("~")
            if prev_line[0] and i > 2:
                data[len(data) - 1]["response"] = (
                    data[len(data) - 1]["response"] + f"\n{line[0]}"
                )

    for entry in data:
        print(
            f"Inserting trigger {entry['trigger']}, image {entry['image']} and response {entry['response']} into the {entry['cardset']} cardset"
        )
        cursor.execute(
            f"DELETE FROM {entry['cardset']} WHERE TRIGGER = ?", [entry["trigger"]]
        )
        cursor.execute(
            f"INSERT INTO {entry['cardset']} VALUES (?,?,?)",
            (entry["trigger"], entry["image"], entry["response"]),
        )
    conn.commit()
