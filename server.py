import random
from collections import deque
from twisted.python import log
from twisted.internet import protocol
from twisted.application import service
from twisted.protocols import basic
from protocol import JsonReceiver
from game import Game, GameError
import simplejson as json

class GameProtocol(JsonReceiver):
    #State definitions for connected players
    STATE_AWAITING_OPPONENT = 1
    STATE_MAKING_MOVE = 2
    STATE_AWAITING_MOVE = 3
    STATE_FINISHED = 4

    def __init__(self):
        self.state = GameProtocol.STATE_AWAITING_OPPONENT
        self.game = None
        self.opponent = None

	#Called when a client-server connection is successfully established
    def connectionMade(self):
        peer = self.transport.getPeer()
        log.msg("Connection made from {0}:{1}".format(peer.host, peer.port))#To Display the connected clients
        self.sendResponse('awaiting_opponent')
        # Find an opponent or add self to a queue
        self.factory.findOpponent(self)

	#Called when connection is terminated
    def connectionLost(self, reason): 
        peer = self.transport.getPeer()
        log.msg("Connection lost from {0}:{1}".format(peer.host, peer.port))
        self.factory.playerDisconnected(self)

	#Overridden function to receive data lines from the clients
    def objectReceived(self, data):
        """Decodes and runs a command from the received data"""
        #log.msg('Data received: {0}'.format(data))
	command = data['command']
        params = data.get('params', {})
	self.runMakeMoveCommand(**params)

	#To send data lines to all clients
    def sendResponse(self, command, **params):
        self.sendObject(command=command, params=params)
        #log.msg("Data sent: {0}({1})".format(command, params))

	#Begin Game by intializing the Player and Opponent
    def startGame(self, game, opponent, side):
        self.game = game
        self.opponent = opponent
        if side == 'X':
            self.state = GameProtocol.STATE_MAKING_MOVE
        else:
            self.state = GameProtocol.STATE_AWAITING_MOVE
        self.sendResponse('started', side=side)#Instruct Clients to START the game
	
	#Executes the move, Updates the board and Changes playing STATES
    def runMakeMoveCommand(self, x, y):
        if self.state == GameProtocol.STATE_MAKING_MOVE:
            self.game.makeMove(x, y)
            self._moveMade(x, y, GameProtocol.STATE_AWAITING_MOVE)#Inform respective clients on Game updates
            self.opponent.makeMoveFromOpponent(x, y)#Opponents turn NEXT
        else:
            self.sendError("Can't make a move right now")
	
	#Change player to opponent
    def makeMoveFromOpponent(self, x, y):
        if self.state == GameProtocol.STATE_AWAITING_MOVE:
            self._moveMade(x, y, GameProtocol.STATE_MAKING_MOVE)
	
	#Update Clients on the latest moves made and STATE changes
    def _moveMade(self, x, y, new_state):
            self.sendResponse('move', x=x, y=y, winner=self.game.getWinner())
            if self.game.isFinished():
                self.state = GameProtocol.STATE_FINISHED
            else:
                self.state = new_state

#The class to handle all protocols and establish the connection
class GameFactory(protocol.ServerFactory):

    protocol = GameProtocol
    queue = deque()#Creating Queue

    def __init__(self, service):
        self.service = service

	#To intialize the respective Player and Opponent 
    def findOpponent(self, player):
        try:
            opponent = self.queue.popleft()#Fetch waiting opponents from the queue
        except IndexError:
            self.queue.append(player)#Add the first player to the queue
        else:
            game = Game()
            side1, side2 = random.choice([('O', 'X'), ('X', 'O')])#Randomly choose X or O

	    """
		Implementing Object Oriented Programming by instantiating different PLAYER and OPPONENT objects
		of the same class GameProtocol with their own Game States and respective values
	    """
            player.startGame(game, opponent, side1) #Player object created
            opponent.startGame(game, player, side2) #Opponent object creates

    def playerDisconnected(self, player):
        try:
            self.queue.remove(player)
        except ValueError:
            pass

class GameService(service.Service):
    pass
