import sys
import json



class Add_route():

    def __init__(self, connection_obj, subparser):
        self.connection_obj = connection_obj
        parser_url = subparser.add_parser('route', help='To use any url described in help')
        parser_url.add_argument('url')
        parser_url.set_defaults(func=self.func())


    def post_json(self):
        pass
    def get_string(self):
        pass
    def get_json(self):
        pass

    def func(self, parsed):
        if parsed.data:
            response = self.connection_obj.post(parsed.url, parsed.data)
        else:
            response = self.connection_obj.get(parsed.url)
        return sys.stdout.write(json.dumps(response))



class Add_Route(Add_Cmd):

    def __init__(self, connection_obj, parser):
        pass

    def func(self):
        pass



    def route(parsed):

