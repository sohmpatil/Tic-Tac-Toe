from twisted.application import internet, service
from server import GameProtocol, GameFactory, GameService
import netifaces

while(1):
    port = int(raw_input("Enter Port >> ")) 
    if (port >= 1024) and (port <= 49151):
        break
    else:
        print("Port can be between 1024–49151")

interface = netifaces.ifaddresses('wlp6s0')[netifaces.AF_INET][0]['addr']

print ("Connecting on {}:{}".format(interface, port))
print

top_service = service.MultiService()

game_service = GameService()
game_service.setServiceParent(top_service)

factory = GameFactory(game_service)
tcp_service = internet.TCPServer(port, factory) 
tcp_service.setServiceParent(top_service)

application = service.Application("twisted-game-server")

top_service.setServiceParent(application)
