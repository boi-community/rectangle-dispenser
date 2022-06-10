import discord
from discord.ext import commands
import os, re, requests, shutil
from thefuzz import fuzz
from thefuzz import process

bot = commands.Bot(command_prefix='!')

# bot token
token = open("tokenFile","r").read().strip()

# userIDs of admins, people who can use ! commands
userIDS = [272773822057414668]


# description of the different datasets. Only hard limit is that the delimiters must be different for each dataset, else only the first one will be considered
data = []
data.append({
	"setName" : "Official Set", 							# name of the set, appears in some responses
	"msgList" : [],											# list of the values, what can be queried with []
	"respList" : [],										# list of the responses, usually a link to the card image
	"fileList" : [],										# list of the paths of cached images, false if no image (to keep indexes consistent with other lists)
	"startDelimiter" : "[[",									# delimiters used for searching in this set
	"endDelimiter" : "]]" ,
	"startDelimiterWithEsc" : "\[\[", 						# escaped delimiters, used when dynamically building the regex used to check what set a query refers to.
	"endDelimiterWithEsc" : "\]\]" ,
	"fileName" : "response.txt",							# source file of the data for this set
	"cacheDir" : "images/",									# storage directory of the cached images
	"imageHostRegex" : "https://i.postimg.cc/.+/.+\.png",	# regex used to detect an image link for a response, used when building images cache
	"separator" : "~"										# separator of the queriable string and the response in the source file
})
data.append({
	"setName" : "Custom Set",
	"msgList" : [],
	"respList" : [],
	"fileList" : [],
	"startDelimiter" : "{",
	"endDelimiter" : "}" ,
	"startDelimiterWithEsc" : "\{",
	"endDelimiterWithEsc" : "\}" ,
	"fileName" : "custom-response.txt",
	"cacheDir" : "custom-images/",
	"imageHostRegex" : "https://i.postimg.cc/.+/.+\.png",
	"separator" : "~"
})


# takes an entry line in set d, downloads it in cache, and rebuilds the lists
def cache_entry(entry, d):
	# adds entry to msg and resp lists
	d["msgList"].append(entry.split(d["separator"])[0].lower())
	d["respList"].append(entry.split(d["separator"])[1])

	# regex to find all links in the response
	imgmatches = re.findall(d["imageHostRegex"], entry.split(d["separator"])[1])
	# continues if only one link
	if (len(imgmatches) == 1):
		# checks if image already exists
		if (not os.path.exists(d["cacheDir"] + imgmatches[0].split("/")[-1])):
			# download image
			res = requests.get(url = imgmatches[0], stream=True)
			if res.status_code == 200:
				# write image to disk
				with open(d["cacheDir"] + imgmatches[0].split("/")[-1], 'wb') as file:
					res.raw.decode_content = True
					shutil.copyfileobj(res.raw, file)
					# copy add image name to file list
					d["fileList"].append(imgmatches[0].split("/")[-1])
					#remove link from response string in memory, to avoid sending the image and the link (would print the image two times), but allow for cases where there is a link and some text
					d["respList"][-1] = d["respList"][-1].replace(imgmatches[0], "")
					print("downloaded " + imgmatches[0].split("/")[-1])
			else: # error log on http errors
				print("error caching file: " + imgmatches[0])
				print(res.status_code)
				print(res.text)
				# false in filelist means the file is not cached
				d["fileList"].append(False)
		else: # handle when the file already exists (do not redownload, to reduce start time), do as if the file was just downloaded
			d["fileList"].append(imgmatches[0].split("/")[-1])
			d["respList"][-1] = d["respList"][-1].replace(imgmatches[0], "")
			print("file already exists: " + imgmatches[0].split("/")[-1])
	elif (len(imgmatches) > 1):	# more than one link, log and do not cache
		d["fileList"].append(False)
		print("more than one link in entry: " + entry + ", canceling cache for this entry")
	elif (len(imgmatches) == 0): # no link, log and do not cache
		d["fileList"].append(False)
		print("no link in entry: " + entry)


# init the detection regex as empty
globalRegex = ""

# loop over all defined datasets
for d in data:
	# create the index file if not existing
	if not (os.path.isfile(d["fileName"])):
		f = open(d["fileName"],"w+")
		f.close()

	#create cache directory if not existing
	if not os.path.exists(d["cacheDir"]):
		os.mkdir(d["cacheDir"])


	#open the file for read and write
	d["filePointer"] = open(d["fileName"],"r+")
	# store read string in set data
	d["readData"] = d["filePointer"].read()
	# put the file pointer back to the beginning, for when the file is rebuilt in !update or !delete
	d["filePointer"].seek(0)
	# separate and store all lines of the file, and remove badly potential garbage entries from file data. filedata is used when the file is rebuilt  
	d["fileData"] = list(filter(lambda x: x != "" and d["separator"] in x , d["readData"].split("\n")))

	# send each line of the file to cache building
	for i in d["fileData"]:
		cache_entry(i, d)

	# adds escaped delimiters for this dataset to the regex. the regex is prebuilt now to avoid doing multiple regex in on_message, for faster processing
	globalRegex = globalRegex + d["startDelimiterWithEsc"] + ".+?" + d["endDelimiterWithEsc"] + "|"

# removing the trailing | from the regex after all datasets have been processed
globalRegex = globalRegex[:-1]

# self explanatory
@bot.event
async def on_ready():
	print("Ready!")

	# sd = 
	# ed = -2
	# print("[[test]]"[2:-2])
	# print("[[test]]"[sd:ed])
	# # print(matches[matchindex][2:-2])


@bot.event
async def on_message(message):
	# process only messages not starting with ! to avoid displaying on commands, and not made by bots
	if (not message.author.bot and message.content != "" and message.content[0] != "!"):
		
		#find all [something] pairs
		matches = re.findall(globalRegex, message.content)
		# init response array
		resarray = []

		#iterate over index of matches (max 3) to reply to all of them
		for matchindex in range(min(len(matches), 3)):


			# iterate over datasets to find the (first) dataset where the delimiters match the match, to find in which dataset to search
			k = 0
			while (k < len(data) and (not matches[matchindex].startswith(data[k]["startDelimiter"]) or not matches[matchindex].endswith(data[k]["endDelimiter"]))):
				k += 1

			# fuzzy string matching, uses the token_sort_ratio method, which priorizes closest match > disordered match > incomplete match. Seems to give the best results in our use case.
			response = process.extractOne(matches[matchindex][len(data[k]["startDelimiter"]):(len(data[k]["endDelimiter"]) * -1)], data[k]["msgList"], scorer=fuzz.token_sort_ratio)[0]

			# nofuzz for windows testing (thefuzz python package is a pain to install on windows) (will create crashes if data that doesn't exactly match is sent, don't run in prod)
			# if matches[matchindex][len(data[k]["startDelimiter"]):len(data[k]["endDelimiter"]) * -1].lower() in data[k]["msgList"]:
			# 	response = matches[matchindex][len(data[k]["startDelimiter"]):len(data[k]["endDelimiter"]) * -1].lower()

			# adds a tuple containting the index of the best response and the dataset it belongs to to the response array
			resarray.append((data[k]["msgList"].index(response), k))

		# iterate over responses array to send responses. uses a counter to detect the first message for the @ reply
		for i in range(len(resarray)):
			# if image has been cached
			#if (data[resarray[i][1]]["fileList"][resarray[i][0]]):
				#read the image
			#	with open(data[resarray[i][1]]["cacheDir"] + data[resarray[i][1]]["fileList"][resarray[i][0]], 'rb') as sendfile:
					#send the reply with file attached(with @ if reply to first match)
			#		await message.channel.send(data[resarray[i][1]]["respList"][resarray[i][0]], reference=(message if i == 0 else None),file=discord.File(sendfile))
			#else:
			if True:
				# send reply with link (or simply text) if file is not cached
				await message.channel.send(data[resarray[i][1]]["respList"][resarray[i][0]], reference=(message if i == 0 else None))

	elif (not message.author.bot and message.content != ""):
		# if !, process commands
		await bot.process_commands(message)

	
@bot.command()
async def add(ctx, *, arg):
	# if admin user
	if ctx.author.id in userIDS:
		# iterate over datasets
		for l in range(len(data)):
			# if separator and delimiters correspond to this dataset
			if (data[l]["separator"] in arg and arg.split(data[l]["separator"])[0].startswith(data[l]["startDelimiter"]) and arg.split(data[l]["separator"])[0].endswith(data[l]["endDelimiter"])):
				# split message (without delimiters) and response
				_message = arg.split(data[l]["separator"])[0][len(data[l]["startDelimiter"]):len(data[l]["endDelimiter"]) * -1]
				rsp = arg.split(data[l]["separator"])[1]
				# respond with error if the entry is not found in this dataset (even though the delimiters and separator match)
				if _message.lower() in data[l]["msgList"]:
					embed=discord.Embed(title="Couldn't Add", description=f"Entry **\'{_message}\'** already exists in \"{data[l]['setName']}\"!\nUse **`!update`** to change its value.", color=0xff0000)
					await ctx.send(embed=embed)
				else:
					#find if there's a link in the new entry
					imgmatches = re.findall(data[l]["imageHostRegex"], rsp)
					if (len(imgmatches) == 1):
						# if exactly one link, download and cache image if the file is new
						if (not os.path.exists(data[l]["cacheDir"] + imgmatches[0].split("/")[-1])):
							res = requests.get(url = imgmatches[0], stream=True)
							# download success
							if res.status_code == 200:
								# write file to disk in proper directory
								with open(data[l]["cacheDir"] + imgmatches[0].split("/")[-1], 'wb') as file:
									res.raw.decode_content = True
									shutil.copyfileobj(res.raw, file)
									# add new data at the bottom of the msg, resp and file lists
									data[l]["msgList"].append(_message.lower())
									data[l]["fileList"].append(imgmatches[0].split("/")[-1])
									data[l]["respList"].append(rsp.replace(imgmatches[0], ""))
									print("downloaded " + imgmatches[0].split("/")[-1])
							else:
								# http error logging and adding new data at the bottom of the msg and resp lists and false at the end of the file list since no cache
								print("error caching file: " + imgmatches[0])
								print(res.status_code)
								print(res.text)
								data[l]["msgList"].append(_message.lower())
								data[l]["fileList"].append(False)
								data[l]["respList"].append(rsp)
						else:
							#see above
							print("file already exists for this entry: " + imgmatches[0].split("/")[-1])
							data[l]["msgList"].append(_message.lower())
							data[l]["fileList"].append(imgmatches[0].split("/")[-1])
							data[l]["respList"].append(rsp.replace(imgmatches[0], ""))
					else:
						#see above too
						print("more than one link or no link in new entry: " + arg)
						print("adding entry without cache")
						data[l]["msgList"].append(_message.lower())
						data[l]["fileList"].append(False)
						data[l]["respList"].append(rsp)

					#writes in the data array (necessary to keep to rebuild file for delete command)
					data[l]["fileData"].append(_message + data[l]["separator"] + rsp)
					#rewrites the file with the new data added at the end (using readData and not fileData to avoid having to rejoin again, for efficiency). Not really necessary to rewrite all, but since the file pointer is already at start and not at the end...
					data[l]["filePointer"].write(data[l]["readData"] + "\n" + _message + data[l]["separator"] + rsp)
					#cuts the rest of the file after write, just in case
					data[l]["filePointer"].truncate()
					#sets the pointer for the next write at beginning of file
					data[l]["filePointer"].seek(0)

					# respond to message
					embed = discord.Embed(title="Message Pair Added!", description=f"Response message has been added!", color=0x00ff00)
					embed.add_field(name="Message", value=_message, inline=True)
					embed.add_field(name="Response", value=rsp, inline=True)
					await ctx.send(embed=embed)
				# adds len of data to the dataset loop counter, then exits the loop. Since this only happens if it has detected the proper dataset, allows for the error response below without having to loop through the rest of the datasets. 
				# Also kind of necessary because I used a for in range, which ends with the counter at len(data - 1) instead of a while which would have ended at 2
				l += len(data)
				break

		# error handling when it has not detected which dataset the entry belongs to. I know it looks fucking weird to have l < len(data) mean that all data has been processed, but trust me it works. It's python that's weird, not my code okay?
		if (l < len(data)):
			embed=discord.Embed(title="Couldn't Add", description=f"Key-value pair **\'{arg}\'** is improperly formatted!", color=0xff0000)
			await ctx.send(embed=embed)

#less comments starting here, because the general structure is pretty close to !add, refer to the comments there
@bot.command()
async def update(ctx,*,arg):
	if ctx.author.id in userIDS:
		for l in range(len(data)):
			if (data[l]["separator"] in arg and arg.split(data[l]["separator"])[0].startswith(data[l]["startDelimiter"]) and arg.split(data[l]["separator"])[0].endswith(data[l]["endDelimiter"])):
				_message = arg.split(data[l]["separator"])[0][len(data[l]["startDelimiter"]):len(data[l]["endDelimiter"]) * -1]
				rsp = arg.split(data[l]["separator"])[1]
				if (_message.lower() not in data[l]["msgList"]):
					embed = discord.Embed(title="Couldn't Update", description=f"Entry **\'{_message}\'** does not exist in \"{data[l]['setName']}\"!", color=0xff0000)
					await ctx.send(embed=embed)
				else:
					# find message to update in filedata and replace it there. not fuzzy of course, here be errors.
					data[l]["fileData"][data[l]["msgList"].index(_message.lower())] = _message + data[l]["separator"] + rsp

					# clear then rebuild lists from updated filedata by calling cache_entry on all entries
					# yes, it shouldn't be necessary to rebuild from scratch, I did this at like 3AM and now I'm afraid it'll break something if I change it
					# I think I did it that way because I was afraid of having temporary discrepancies between the lists when another request comes, which could create crashes or break things, but I'm not sure that's the best way to go about it
					data[l]["msgList"].clear()
					data[l]["respList"].clear()
					data[l]["fileList"].clear()
					for i in data[l]["fileData"]:
						cache_entry(i, data[l])

					# detect link(s) in new value
					imgmatches = re.findall(data[l]["imageHostRegex"], rsp)
					if (len(imgmatches) == 1):
						# if one link in new value, download the file even if it already exists (useful to correct or update a cached image), and must be done because cache_entry doesn't redownload if image exists
						res = requests.get(url = imgmatches[0], stream=True)
						if res.status_code == 200:
							with open(data[l]["cacheDir"] + imgmatches[0].split("/")[-1], 'wb') as file:
								res.raw.decode_content = True
								shutil.copyfileobj(res.raw, file)
								print("downloaded " + imgmatches[0].split("/")[-1])
						#do nothing except logging in case of http error when caching, since the lists have already been properly rebuilt by cache_entry
						else:
							print("error caching file: " + imgmatches[0])
							print(res.status_code)
							print(res.text)
					else:
						#same as above, no need to modify the lists any more if no caching to do
						print("more than one link (or no link) in new entry: " + arg)
						print("canceling cache for this entry")

					# writes in the index file (overwriting contents). Can't use readData as in !update here, because the change is not at the end of the string and searching for the right place to modify would be even less efficient than joining
					data[l]["filePointer"].write("\n".join(data[l]["fileData"]))
					# cuts the rest of the file after write (mandatory in case the new content is shorter)
					data[l]["filePointer"].truncate()
					# sets the pointer for the next write at beginning of file
					data[l]["filePointer"].seek(0)

					embed=discord.Embed(title="Message Pair Added!", description=f"Entry **\'{_message}\'** has been updated!", color=0x00ff00)
					embed.add_field(name="Message", value=_message, inline=True)
					embed.add_field(name="Response", value=rsp, inline=True)
					await ctx.send(embed=embed)

				l += len(data)
				break

		if (l < len(data)):
			embed=discord.Embed(title="Couldn't Update", description=f"Key-value pair **\'{arg}\'** is improperly formatted!", color=0xff0000)
			await ctx.send(embed=embed)

#less comments here too, same shit
@bot.command()
async def delete(ctx,*,arg):
	if ctx.author.id in userIDS:
		for l in range(len(data)):
			#only check for the dataset by delimiters here, since the command does not use the separator and after
			if (arg.startswith(data[l]["startDelimiter"]) and arg.endswith(data[l]["endDelimiter"])):
				if (arg[len(data[l]["startDelimiter"]):len(data[l]["endDelimiter"]) * -1].lower() in data[l]["msgList"]):
					#find the index of the entry to delete in the arrays. no fuzzy search for you. obviously.
					indx = data[l]["msgList"].index(arg[len(data[l]["startDelimiter"]):len(data[l]["endDelimiter"]) * -1].lower())
					
					#copy value for deletion acknowledgement response
					valbck = data[l]["respList"][indx]
					filebck = data[l]["fileList"][indx]

					#remove from arrays
					data[l]["fileData"].pop(indx)
					data[l]["msgList"].pop(indx)
					data[l]["respList"].pop(indx)
					data[l]["fileList"].pop(indx)

					#respond to the request, with an embed file if the entry was cached, or just text/link if not
					embed = discord.Embed(title="Entry Deleted!", description=f"Entry **\'{arg}\'** has been deleted!", color=0x00ff00)
					embed.add_field(name="Message", value=arg, inline=True)
					if (filebck):
						file = discord.File(data[l]["cacheDir"] + filebck, filename="image.png")
						embed.set_image(url="attachment://image.png")
						await ctx.send(file=file, embed=embed)
					else:
						embed.add_field(name="Response", value=valbck, inline=True)
						await ctx.send(embed=embed)
					
					#rebuild the file, same as in !update
					data[l]["filePointer"].write("\n".join(data[l]["fileData"]))
					data[l]["filePointer"].truncate()
					data[l]["filePointer"].seek(0)
				else:
					#entry not found logging
					embed = discord.Embed(title="Couldn't Delete", description=f"Entry **\'{arg}\'** does not exist in \"{data[l]['setName']}\"!", color=0xff0000)
					await ctx.send(embed=embed)
				l += len(data)
				break

		if (l < len(data)):
			embed=discord.Embed(title="Couldn't Delete", description=f"Value **\'{arg}\'** is improperly formatted!", color=0xff0000)
			await ctx.send(embed=embed)

# !usage command (as !help is a discord.py default and could not be used). Content is a copy of [Help]
@bot.command()
async def usage(ctx,*,arg):
	ctx.send("To use this bot, just type the name of a card surrounded by these brackets, for example, [Cain]. You can also use this bot to get a link to the ‘Official Table’ and the ‘Scripted Table’ on Tabletop Simulator.")


bot.run(token)


# TODO:
# validation check for delete (and update?), with emoji reactions maybe, is that a good UX?
# (better) help command ?
# use the foursouls.com api, maybe for card names, if kizzy implements aliases maybe?
# commenting pass
# more logging & error handling!
# !list command ?
# remove delimiters from storage and display
# handle multiple links in one response?
# proper database instead of files
# dataset info in database
# @reply to all messages and not only the first?
# maybe avoid rebuilding from scratch? (see line 270 comments)
# embed file in response to add and update
# token from config file