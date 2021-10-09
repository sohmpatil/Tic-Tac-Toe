#!/usr/bin/env python
import optparse
import re
from functools import partial
from twisted.protocols import basic
from twisted.internet import protocol, stdio
from protocol import JsonReceiver
from game import Game
import simplejson as json
from twisted.protocols import basic

# Callback is a method in LineReceiver Protocol Module

# Class Inherits methods of LineReceiver from basic module of Twisted API
class UserInputProtocol(basic.LineReceiver):
    from os import linesep as delimiter
    def __init__(self, callback):
        self.callback = callback

    def lineReceived(self, line):
        self.callback(line)

# Main game client class, starts game server on client side
# All client side message control flow and moves are made in this class
# Class inherits methods of JsonReceiver
class GameClientProtocol(JsonReceiver):

    # Instantiate game obj and set side to None
    def __init__(self):
        self.game = Game()
        self.side = None

    # Function to print messages of variable parameters
    def out(self, *messages):
        for message in messages:
            print message

    # Print help and board after connection is made
    def connectionMade(self):
        stdio.StandardIO(UserInputProtocol(self.userInputReceived))
        self.out("Connected!")
        self.printHelp()
        self.printBoard()

    def userInputReceived(self, string):
        # A database of commands, with command as key
        commands = {
                    'start': self.sendStartGame,
                    '?': self.printHelp,
                    'h': self.printHelp,
                    'help': self.printHelp,
                    'p': self.printBoard,
                    'print': self.printBoard,
                    'm': self.sendMakeMove,
                    'move': self.sendMakeMove,
                    'q': self.exitGame,
                    'quit': self.exitGame,
                    'exit': self.exitGame,
                    }

        # Cant make move if not current player
        if self.game.current_player != self.side:
            self.out("You cant make a move!")
            return

        # Regular expressions are used to search for two '1 to 3' input characters
        match = re.match('^\s*([123])\s*([123])\s*$', string)
        if match:
            command = 'move'
            # Groups will join both the matched regular expression outputs
            params = match.groups()
        else:
            # Filter filters out the values which returns True value for function given as parameter
            params = filter(len, string.split(' '))
            command, params = params[0], params[1:]

        # If not in database, return with no value
        if not command:
            return

        #Checks for re-entry of cell block, and non-zero value of parameters
        board = [[cell or ' ' for cell in col] for col in self.game.board]
        if (len(params) != 0) and  (board[int(params[1]) - 1][int(params[0]) - 1] != ' '):
            self.out("Can't make that move")
            return

        # If no command found in the database, return with Null value
        if command not in commands:
            self.out("Invalid command")
            return

        # Try, exception method used to execute commands in the database,
        # if some error is raised, raise invalid parameters message and exit
        try:
            commands[command](*params)
        except TypeError, e:
            self.out("Invalid command parameters: {0}".format(e))

    def printHelp(self):
        self.out(
            "",
            "Available commands:",
            "  ?, h, help          - Print list of commands",
            "  p, print            - Print the board",
            "  <row><col>          - Make a move to a cell located in given row/column",
            "                        \"row\" and \"col\" should be values between 1 and 3",
            "  q, quit, exit       - Exit the program",
            "")

    # Destroy the connection
    def exitGame(self):
        self.out("Disconnecting...")
        self.transport.loseConnection()

    # Sends commands using the Json format
    def sendCommand(self, command, **params):
        self.sendObject(command=command, params=params)

    # Send start game command
    def sendStartGame(self):
        self.sendCommand('start')

    # Send make move command, with x, y <row><col> parameters
    def sendMakeMove(self, row, col):
        self.sendCommand('move', x=col, y=row)

    # Json command receive function, calls the receiveCommand method
    def objectReceived(self, obj):
        if obj.has_key('command'):
            command = obj['command']
            params = obj.get('params', {})
            self.receiveCommand(command, **params)

    # Not implemented method
    def invalidJsonReceived(self, data):
        pass

    def receiveCommand(self, command, **params):
        # This database is defined to the control flow of peer to peer game queue
        commands = {
            'error': self.serverError,
            'move': self.serverMove,
            'awaiting_opponent': partial(self.serverMessage, "Please wait for another player"),
            'opponent_disconnected': self.serverOpponentDisconnected,
            'started': self.serverStarted,
            }

        if command not in commands:
            return

        try:
            commands[command](**params)
        except TypeError, e:
            pass

    def serverError(self, message):
        self.out("Server error: {0}".format(message))

    def serverMessage(self, message):
        self.out(message)

    # Marks the board and checks for winner
    # If winner is present, prints "won/lost" message, else calls for draw
    def serverMove(self, x, y, winner=None):
        self.game.makeMove(x, y)
        self.printBoard()
        if winner is None:
            self.printNextTurnMessage()
        else:
            if winner == self.side:
                self.out("You won, congratulations!")
            elif winner != 'D':
                self.out("You've lost...")
            else:
                self.out("Its a draw!!")
            self.exitGame()

    # Server control flow methods
    # Initiate game on both clients
    def serverStarted(self, side):
        self.side = side
        self.out("Game started, you're playing with {0}".format(side))
        self.printNextTurnMessage()

    # End game if one client disconnects
    def serverOpponentDisconnected(self):
        self.out("Your opponent has disconnected, game is over")
        self.exitGame()

    # Print whose turn it is
    def printNextTurnMessage(self):
        if self.game.current_player == self.side:
            self.out("It's your turn now")
        else:
            self.out("It's your opponent's turn now")

    # Print board in format
    def printBoard(self):
        board = [[cell or ' ' for cell in col] for col in self.game.board]
        lines = [
                 "     1   2   3",
                 "   +---+---+---+",
                 " 1 | {0[0]} | {1[0]} | {2[0]} |",
                 "   +---+---+---+",
                 " 2 | {0[1]} | {1[1]} | {2[1]} |",
                 "   +---+---+---+",
                 " 3 | {0[2]} | {1[2]} | {2[2]} |",
                 "   +---+---+---+",
                 "",
                 ]
        self.out("\n".join(lines).format(*board))


# Inherits from ClientFactory from protocol module of Twisted API
class GameClientFactory(protocol.ClientFactory):
    # Asserts the protocol to the local GameClientProtocol, which will be called in API module
    protocol = GameClientProtocol

    # Twisted Factory methods
    def startedConnecting(self, connector):
        destination = connector.getDestination()
        print "Connecting to server {0}:{1}, please wait...".format(destination.host, destination.port)

    def clientConnectionFailed(self, connector, reason):
        print reason.getErrorMessage()
        from twisted.internet import reactor
        reactor.stop()  #@UndefinedVariable

    def clientConnectionLost(self, connector, reason):
        print reason.getErrorMessage()
        from twisted.internet import reactor, error
        try:
            reactor.stop()  #@UndefinedVariable
        except error.ReactorNotRunning:
            pass

# This method is used to parse the terminal arguments.
# If the input is "./run-client" then the host is localhost and the port number is 20000 (default)
# If the input is "./run-client 1234", it means host is localhost and port number is 1234
# If the input is "./run-client 192.168.0.2:1234" then IP address is 192.168.0.2 and port number is 1234
def parse_args():
    usage = "usage: %prog [options] [[hostname:]port]"

    parser = optparse.OptionParser(usage)

    _, args = parser.parse_args()

    if not args:
        address = "127.0.0.1:20000"
    else:
        address = args[0]

    if ':' not in address:
        host, port = '127.0.0.1', address
    else:
        host, port = address.split(':', 1)

    if not port.isdigit():
        parser.error("Ports must be integers.")

    return host, int(port)

def run_client():
    # Reactor runs in a main loop, accepting string from user and parsing them to the server,
    # using the TCP protocol.
    from twisted.internet import reactor
    host, port = parse_args()
    factory = GameClientFactory()
    reactor.connectTCP(host, port, factory)
    reactor.run()

# Function call when program is executed
if __name__ == '__main__':
    run_client()
