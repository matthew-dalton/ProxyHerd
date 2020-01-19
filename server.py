# Matthew Dalton
# mattdalton@ucla.edu
# 304964539

import asyncio
import json
import aiohttp
import logging
import re
import time


# GLOBAL VARIABLES

# ports local to your computer --> might need to be changed
ports = {
			'Goloman' : 11652,
			'Hands' : 11653,
			'Holiday' : 11654,
			'Welsh' : 11655,
			'Wilkes' : 11656
}

# describes the relationships between servers
neighbors = {
			'Goloman' : ['Hands','Holiday','Wilkes'],
			'Hands' : ['Goloman', 'Wilkes'],
			'Holiday' : ['Goloman', 'Welsh', 'Wilkes'],
			'Welsh' : ['Holiday'],
			'Wilkes' : ['Goloman', 'Hands', 'Holiday']
}

# describes the status of each server
servers = {
			'Goloman' : '',
			'Hands' : '',
			'Holiday' : '',
			'Welsh' : '',
			'Wilkes' : ''
}

# keys are user IDs, values are [response, latitude, longitude, timestamp]
locations = {}


BAD_ARG = 1

my_log = logging.getLogger("my_log")

# unknown as of yet
server_name = ''

# your unique API key
API_KEY = ''

# base url for http requests
BASE_URL = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json?'


# regular expressions for interpreting input commands
IAMAT_RE = r'^IAMAT\s+(.*)\s+([+-][0-9]*\.[0-9]*)([+-][0-9]*\.[0-9]*)\s+([0-9]*\.[0-9]*)\s*'
WHATSAT_RE = r'^WHATSAT\s+(.*)\s+([0-9]|[1-4][0-9]|50)\s+([0-9]|1[0-9]|20)\s*'
AT_RE = r'From\s+(.*):\s+(AT\s+(.*)\s+([+-][0-9]*\.[0-9]*)\s+(.*)\s+([+-][0-9]*\.[0-9]*)([+-][0-9]*\.[0-9]*)\s+([0-9]*\.[0-9]*))\s*'

####################################################################################
############################# HANDLER FUNCTION #####################################
####################################################################################

async def handle_connection(reader, writer):
	# define these global variables
	global ports
	global neighbors
	global servers
	global locations
	global my_log
	global server_name

	# read what client said
	data = await reader.read()

	# return if client closes connection
	if (data == b''):
		writer.close()
		return

	# decode what client said
	message = data.decode()

	# log what client said
	my_log.info(message)


	######################################################################
	######################## IAMAT Command ###############################
	######################################################################
	
	# check if client sent an IAMAT command
	matchObj = re.fullmatch(IAMAT_RE, message)
	if matchObj:

		# Get fields from regular expression
		groups = matchObj.groups()
		userID = groups[0]
		latitude = groups[1]
		longitude = groups[2]
		timestamp = groups[3]

		# Construct response to IAMAT command
		location = f'{latitude}{longitude}'
		diff = float(time.time()) - float(timestamp)
		timeDiff = f'+{diff}' if diff >= 0 else f'{diff}'
		response = f'AT {server_name} {timeDiff} {userID} {location} {timestamp}\n'

		# check if IAMAT message contains new information
		# the third index of locations[userID] is the timestamp of the last information
		if (userID not in locations) or (locations[userID][3] < timestamp):

			# add our response and the new location to our dictionary
			locations[userID] = [response,latitude,longitude,timestamp]

			# try to flood response to other servers
			for neighbor in neighbors[server_name]:
				try:

					# attempt to establish connection
					reader1, writer1 = await asyncio.open_connection('127.0.0.1', ports[neighbor])

					# write flood message to neighbor
					flood = f'From {server_name}: {response}\n'
					writer1.write(flood.encode())
					writer1.write_eof()
					await writer1.drain()
					writer1.close()

					# check if connection was new
					if (servers[neighbor] != 'up'):
						my_log.info(f'Opened connection with {neighbor}\n')
						servers[neighbor] = 'up'

					# log flood message
					my_log.info(f'To {neighbor}: {flood}\n')

					# log flood response
					neighbor_reply = await reader1.read()
					my_log.info(f'From {neighbor}: {neighbor_reply.decode()}\n')

				# could not establish connection with neighbor
				except:

					if (servers[neighbor] == 'up'):
						servers[neighbor] = 'down'
						my_log.info(f'Lost connection with {neighbor}\n')

		# respond to client
		my_log.info(response)
		writer.write(response.encode())
		writer.write_eof();
		await writer.drain()
		writer.close()
		return



	######################################################################
	####################### WHATSAT Command ##############################
	######################################################################

	# check if client sent a WHATSAT command
	matchObj = re.fullmatch(WHATSAT_RE, message)
	if matchObj:

		# grab parts from input
		groups = matchObj.groups()
		userID = groups[0]
		radius = groups[1]
		max_results = int(groups[2])

		# invalid command
		if (userID not in locations) or (int(radius) <= 0) or (int(max_results) < 0) or (int(radius) > 50) or (int(max_results) > 20):
			# construct response to invalid command
			response = f'? {message}'

			# respond to client
			my_log.info(response)
			writer.write(response.encode())
			writer.write_eof();
			await writer.drain()
			writer.close()
			return

		# get location information
		at_response = locations[userID][0]
		latitude = locations[userID][1]
		longitude = locations[userID][2]
		location = f'{latitude},{longitude}'

		# send http request to google places
		json_dict = await sendHTTP(f'{BASE_URL}location={location}&radius={radius}&key={API_KEY}')
		
		# make sure we are within max result count
		json_dict['results'] = json_dict['results'][0:max_results]

		json_string = json.dumps(json_dict, indent=4)

		# construct response to WHATSAT query
		# NOT SURE IF THIS WORKS
		# response3 = f'{at_response}{json_string}' # add two newlines to the end of this if third line doesn't work
		# response2 = response3.replace(':', ' :') # definitely works
		# response1 = response2.replace(r'\n+', '\n') # might not work
		# response = f'{response1}\n\n' # definitely works

		response1 = f'{at_response}{json_string}\n\n'
		response = response1.replace(':', ' :')

		# respond to client
		my_log.info(response)
		writer.write(response.encode())
		writer.write_eof();
		await writer.drain()
		writer.close()
		return



	######################################################################
	########################## AT Command ################################
	######################################################################

	# check if client sent a AT command (a propagation from another server)
	matchObj = re.fullmatch(AT_RE, message)
	if matchObj:

		# grab parts from input
		groups = matchObj.groups()
		sender = groups[0]
		info = groups[1]
		userID = groups[4]
		latitude = groups[5]
		longitude = groups[6]
		timestamp = groups[7]

		# check if message is new information -- prevents infinite flooding
		if (userID not in locations) or (locations[userID][3] < timestamp):

			# add new information to locations dictionary
			locations[userID] = [info,latitude,longitude,timestamp]

			# flood new information to neighbors
			for neighbor in neighbors[server_name]:
				try:
					
					# attempt to establish connection
					reader2, writer2 = await asyncio.open_connection('127.0.0.1', ports[neighbor])

					# write flood message to neighbor
					flood = f'From {server_name}: {info}\n'
					writer2.write(flood.encode())
					writer2.write_eof()
					await writer2.drain()
					writer2.close()

					# check if connection was new
					if (servers[neighbor] != 'up'):
						my_log.info(f'Opened connection with {neighbor}\n')
						servers[neighbor] = 'up'

					# log flood message
					my_log.info(f'To {neighbor}: {flood}\n')

					# log flood response
					neighbor_reply = await reader2.read()
					my_log.info(f'From {neighbor}: {neighbor_reply.decode()}\n')

				# could not establish connection with neighbor
				except:

					if (servers[neighbor] == 'up'):
						servers[neighbor] = 'down'
						my_log.info(f'Lost connection with {neighbor}\n')


		# respond to neighbor confirming receipt of message
		response = f'{server_name} received from {sender}: {info}'
		my_log.info(response)
		writer.write(response.encode())
		# writer.write_eof();
		await writer.drain()
		writer.close()
		return
	


	######################################################################
	######################## Invalid Command #############################
	######################################################################

	# client did not send a valid command
	# construct response to invalid command
	response = f'? {message}'

	# respond to client
	my_log.info(response)
	writer.write(response.encode())
	writer.write_eof();
	await writer.drain()
	writer.close()
	return

####################################################################################
############################## END OF FUNCTION #####################################
####################################################################################

# wrapper function to fetch data
async def fetch(session, url):
    async with session.get(url) as response:
        return await response.json()

# wrapper function for sending http
async def sendHTTP(url):
	async with aiohttp.ClientSession() as session:
		return await fetch(session, url)


####################################################################################
############################## MAIN SCRIPT STUFF ###################################
####################################################################################

# begins the program
async def main():
	my_log = logging.getLogger("my_log")
	servers[server_name] = 'self'
	server = await asyncio.start_server(handle_connection,host='127.0.0.1',port=ports[server_name])
	await server.serve_forever()

if __name__ == "__main__":
	import sys

	if len(sys.argv) != 2:
		print("server.py: please include one of the following servers you would like to start:")
		print("Goloman, Hands, Holiday, Welsh, Wilkes")
		sys.exit(BAD_ARG)

	server_name = sys.argv[1]
	if not (server_name == 'Goloman' or server_name == 'Hands' or server_name == 'Holiday' or server_name == 'Welsh' or server_name == 'Wilkes'):
		print("server.py: please include one of the following servers you would like to start:")
		print("Goloman, Hands, Holiday, Welsh, Wilkes")
		sys.exit(BAD_ARG)

	asyncio.run(main())