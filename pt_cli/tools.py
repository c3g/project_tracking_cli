import sys
import json
import argparse


class AddCMD:
    __tool_name__ = 'tool_name'
    """
    {} is the basic class to write pt_cli tools
    Write the tool help as a string here
    """.format(__tool_name__)
    def __init__(self, connection_obj, subparser=argparse.ArgumentParser().add_subparsers()):
        """
        :param connection_obj: helps to Connect and identify yourself to the Database api
        :param subparser: arguments that triggers the tool, The default is set here to help the autocomplete
        """
        self.connection_obj = connection_obj
        self.parser = subparser.add_parser(self.__tool_name__, help=self.help())
        self.arguments()
        self.parser.set_defaults(func=self.func)
        self.project_name = self.connection_obj.project_name

    def data(self, parsed_args, error_if_missing=True):
        """

        :param parsed_args: argument form the command lines
        :param error_if_missing: Will raise Error when true and no data is provided
        :return: the data as a string
        """

        if parsed_args.data:
            return parsed_args.data
        elif parsed_args.data_file:
            return parsed_args.read()
        elif error_if_missing:
            raise ValueError(f'Data inputs is needed for the "{self.__tool_name__}" subcommnad')


    def post(self,path, data):
        self.connection_obj.post(path, data=data)

    def get(self, path):
        self.connection_obj.get(path)

    def help(self):
        """
        :return: the tool help string
        """
        raise NotImplementedError

    def arguments(self):
        """
        add your arguments to self.parser here
        :return:
        """
        raise NotImplementedError

    def func(self, parsed):
        """ This function is the entry point of the tool/object. It receives parsed arguments

        :param parsed: aguments form the command lines
        :return: None
        """
        raise NotImplementedError




class ReadsetFile(AddCMD):
    __tool_name__ = 'readset_file'
    def __init__(self, *args, **kwargs):
        super(ReadsetFile, self).__init__(*args, **kwargs)
        self. json_list = None
        self.output_file = None

    def help(self):
        return "Will return a Genpipes readset file in a csv format"

    def arguments(self):
        self.parser.add_argument('input_type', choices=['readsets', 'samples'])
        self.parser.add_argument('output', default="readset_file.csv")

    def readsets(self):
        '''
        organise stuff here when readset is in the list
        :return:
        '''

        self.get(f'project/{self.project_name}/digest_readset')

    def samples(self):
        '''
        organise stuff here when sample is in the list
        :return:
        '''

        self.get(f'project/{self.project_name}/digest_sample')

    def func(self, parsed_args):
        self.json_list = json.loads(self.data(parsed_args))
        self.output_file = parsed_args.output

        objet_name = True
        if isinstance(int, self.json_list[0]):
            # using objects id
            objet_name = False

        getattr(self, parsed_args.input_type)
