# ProxyHerd
Application Server Herd prototype using Python's asyncio (Python 3.7.2)

This prototype explores an alternative to a traditional LAMP platform in order to accomodate a hypothetical service that requires suitability for:
  * frequent updates
  * protocols other than just HTTP
  * more mobile clients

The idea is that each server communicates directly with its neighbors, rather that with a central server, in order to propagate data to *all* connected servers, that is, the neighbors of its neighbors, and their neibors, and so on.

To implement this prototype, I use python's asynchronous netoworking library, 'asyncio'.


### THE FUNCTIONALITY:

The prototype consists of 5 servers with IDs 'Goloman', 'Hands', 'Holiday', 'Welsh', and 'Wilkes' (can you guess why?). They communicate bidirectionally with each other as follows:
  * Goloman talks with Hands, Holiday, and Wilkes
  * Hands talks with Wilkes
  * Holiday talks with Welsh and Wilkes

Each server accepts TCP connections from clients. A client can send its location using the following format:

`IAMAT kiwi.cs.ucla.edu +34.068930-118.445127 1520023934.918963997`

The first field is the name of the command. Its operands are the client ID, the latitude and longitude in decimal degrees using ISO 6709 notation, and the clien't idea of when it sent the message expressed in POSIX time, respectively.

The server should respond to clients with a message using the following format:

`AT Goloman +0.263873386 kiwi.cs.ucla.edu +34.068930-118.445127 1520023934.918963997`

The first field is the name of the command. Its operands are the ID of the server that received the message, the difference between when the server thinks it got the message and when the sender thinks they sent it, and then a copy of the operands from the corresponding IAMAT command, respectively.

Clients may also query for information about places near other clients' locations using:

`WHATSAT kiwi.cs.ucla.edu 10 5`

The operands are the name of another client, a kilometric radius from the client, and an upperbound on the amount of information to receive from Google Places data within the requested radius.

The server then responds with an AT message in the same format as before, followed by a JSON-format message containing the requested places data:

`AT Goloman +0.263873386 kiwi.cs.ucla.edu +34.068930-118.445127 1520023934.918963997`
*Insert JSON Message*

Invalid commands are responded to with a questions mark, followed by that very same erroneous command.



A simple flooding algorithm is used for interserver location information propagation.

### HOW TO USE IT:

To properly test this prototype, it is necessary to have several instances of the program running, ideally 5, in order to have each different server ID running.

To launch the program, use:

`./server.py server_ID`

Where 'server_name' is one of the 5 server IDs mentioned above. This will launch that server on the port specified in the python file.

You can use the 'nc' or 'telnet' commands to connect to a server (obviously a running server) in order to send it messages and test its functionality.

In order to access the google places API, you need to obtain a unique API key by [enabling an API](https://console.developers.google.com/flows/enableapi?apiid=places_backend&keyType=SERVER_SIDE&reusekey=true) and placing your unique key in server.py.
