import sys
import json
import argparse
import csv


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
            data = parsed_args.data_file.read()
            parsed_args.data_file.close()
            return data
        elif error_if_missing:
            raise ValueError(f'Data inputs is needed for the "{self.__tool_name__}" subcommnad')


    def post(self, path, data):
        return self.connection_obj.post(path, data=data)

    def get(self, path):
        return self.connection_obj.get(path)

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
    READSET_HEADER = [
            "Sample",
            "Readset",
            "LibraryType",
            "RunType",
            "Run",
            "Lane",
            "Adapter1",
            "Adapter2",
            "QualityOffset",
            "BED",
            "FASTQ1",
            "FASTQ2",
            "BAM"
            ]
    def __init__(self, *args, **kwargs):
        super(ReadsetFile, self).__init__(*args, **kwargs)
        self.readsets_samples_input = None
        self.output_file = None

    def help(self):
        return "Will return a Genpipes readset file in a csv format"

    def arguments(self):
        # self.parser.add_argument('input_type', choices=['readsets', 'samples'])
        self.parser.add_argument('--output', '-o', default="readset_file.tsv")

    @property
    def readset_file(self):
        '''
        organise stuff here when readset is in the list
        :return:
        '''
        return self.post(f'project/{self.project_name}/digest_readset_file', data=json.loads(self.readsets_samples_input))

    def json_to_readset_file(self):
        with open(self.output_file, "w", encoding="utf-8") as out_readset_file:
            tsv_writer = csv.DictWriter(out_readset_file, delimiter='\t', fieldnames=self.READSET_HEADER)
            tsv_writer.writeheader()
            for readset_line in self.readset_file:
                tsv_writer.writerow(readset_line)

    def func(self, parsed_args):
        self.readsets_samples_input = json.dumps(self.data(parsed_args))
        self.output_file = parsed_args.output

        self.json_to_readset_file()
