import logging
import sys
import json
import argparse
import csv

logger = logging.getLogger(__name__)

class AddCMD:
    __tool_name__ = 'tool_name'
    """
    AssCMD is the basic class to write pt_cli tools.
    To create a new subcommand, create a child class 
    and write help(), arguments() and func() methods 
    """.format(__tool_name__)

    _POSTED_DATA = None

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
        self.parsed_args = None

    def data(self, error_if_missing=True):
        """
        :param error_if_missing: Will raise Error when true and no
        data is provided
        :return: The data to be posted to the server. This will be a
        string coming from a user provided file or directly from the
        command line

        """
        if self._POSTED_DATA is None:
            if self.parsed_args.data:
                self._POSTED_DATA = self.parsed_args.data
            elif self.parsed_args.data_file:
                self._POSTED_DATA = self.parsed_args.data_file.read()
                self.parsed_args.data_file.close()
            elif error_if_missing:
                raise ValueError(f'Data inputs is needed for the "{self.__tool_name__}" subcommand')

        return self._POSTED_DATA

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
        Add your arguments to self.parser here.
        :return:
        """
        pass

    def func(self, parsed_args):
        """ This function is the entry point of the tool/object. It receives parsed arguments.
        It needs to be reimplemented in children classes in this way:

            def func(self, parsed_args):
                super().func(parsed_args)


        :param parsed_args: arguments form the command lines
        :return: None
        """
        self.parsed_args = parsed_args


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
        super().__init__(*args, **kwargs)
        self.readsets_samples_input = None
        self.output_file = None

    def help(self):
        return "Will return a Genpipes readset file in a tsv format"

    def arguments(self):
        self.parser.add_argument('--output', '-o', default="readset_file.tsv")

    @property
    def readset_file(self):
        '''
        Returns a list of readset lines of GenPipes of the API call for digest_readset_file
        :return:
        '''
        return self.post(f'project/{self.project_name}/digest_readset_file',
                         data=self.readsets_samples_input)

    def json_to_readset_file(self):
        with open(self.output_file, "w", encoding="utf-8") as out_readset_file:
            tsv_writer = csv.DictWriter(out_readset_file, delimiter='\t', fieldnames=self.READSET_HEADER)
            tsv_writer.writeheader()
            for readset_line in self.readset_file:
                tsv_writer.writerow(readset_line)
            logger.info(f"Readset file written to {self.output_file}")

    def func(self, parsed_args):
        super().func(parsed_args)
        self.readsets_samples_input = self.data()
        self.output_file = parsed_args.output
        self.json_to_readset_file()

class PairFile(AddCMD):
    __tool_name__ = 'pair_file'
    PAIR_HEADER = [
            "Patient",
            "Sample_N",
            "Sample_T"
            ]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.readsets_samples_input = None
        self.output_file = None

    def help(self):
        return "Will return a Genpipes pair file in a csv format"

    def arguments(self):
        self.parser.add_argument('--output', '-o', default="pair_file.csv")

    @property
    def pair_file(self):
        '''
        Returns a list of pair lines of GenPipes of the API call for digest_pair_file
        :return:
        '''
        return self.post(f'project/{self.project_name}/digest_pair_file',
                         data=self.readsets_samples_input)

    def json_to_pair_file(self):
        with open(self.output_file, "w", encoding="utf-8") as out_pair_file:
            tsv_writer = csv.DictWriter(out_pair_file, delimiter=',', fieldnames=self.PAIR_HEADER)
            # tsv_writer.writeheader()
            for pair_line in self.pair_file:
                tsv_writer.writerow(pair_line)
            logger.info(f"Pair file written to {self.output_file}")

    def func(self, parsed_args):
        super().func(parsed_args)
        self.readsets_samples_input = self.data()
        self.output_file = parsed_args.output
        self.json_to_pair_file()
