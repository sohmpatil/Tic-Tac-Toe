import simplejson as json
from twisted.protocols import basic

class JsonReceiver(basic.LineReceiver):
    def lineReceived(self, data):
	decoded_data = json.loads(data)
        self.objectReceived(decoded_data)

    def objectReceived(self, obj):
        pass

    def sendObject(self, obj=None, **kwargs):
        dict = {}
        if obj is not None:
            dict.update(obj)
        if kwargs is not None:
            dict.update(kwargs)
        self.sendLine(json.dumps(dict))
