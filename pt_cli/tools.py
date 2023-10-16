import logging
import sys
import json
import argparse
import csv

logger = logging.getLogger(__name__)

def unroll(string):
    """
    string: includes number in the "1,3-7,9" form
    return: a list if int of the form [1,3,4,5,6,7,9]
    """

    elem = [e for e in string.split(',') if e]
    unroll_list = []
    for e in elem:
        if '-' in e:
            first = int(e.split('-')[0])
            last = int(e.split('-')[-1])
            for i in range(min(first,last), max(first,last) + 1):
                unroll_list.append(int(i))
        else:
            unroll_list.append(int(e))

    return unroll_list

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
        self.parser = subparser.add_parser(self.__tool_name__, help=self.help(), add_help=True)
        self.arguments()
        self.parser.set_defaults(func=self.func)
        self.project_id = self.connection_obj.project_id
        self.parsed_args = None

    def data(self, error_if_missing=False):
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
        """
        This function is the entry point of the tool/object. It receives parsed arguments.
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
        return "Will return a Genpipes readset file in a tsv format. /!\\ Either use --input-json OR --sample_<name|id>/--readset_<name|id> + --endpoint arguments"

    def arguments(self):
        self.parser.add_argument('--output', '-o', default="readset_file.tsv", help="Name of readset file returned (Default: readset_file.tsv)")
        self.parser.add_argument('--sample_name', help='Sample Name to be selected', nargs='+')
        self.parser.add_argument('--readset_name', help='Readset Name to be selected', nargs='+')
        self.parser.add_argument('--sample_id', help='Sample ID to be selected', nargs='+')
        self.parser.add_argument('--readset_id', help='Readset ID to be selected', nargs='+')
        self.parser.add_argument('--endpoint', help="Endpoint in which data is located")
        self.parser.add_argument('--input-json', help="Json file with sample/readset and endpoint to be selected")

    @property
    def readset_file(self):
        '''
        Returns a list of readset lines of GenPipes of the API call for digest_readset_file
        :return:
        '''
        return self.post(f'project/{self.project_id}/digest_readset_file', data=self.readsets_samples_input)

    def jsonify_input(self, parsed_args):
        json = {
            "location_endpoint": parsed_args.endpoint
        }
        if parsed_args.sample_name:
            json["sample_name"] = list(parsed_args.sample_name)
        if parsed_args.sample_id:
            if len(parsed_args.sample_id) == 1:
                json["sample_id"] = unroll(parsed_args.sample_id[0])
            else:
                json["sample_id"] = parsed_args.sample_id
        if parsed_args.readset_name:
            json["readset_name"] = list(parsed_args.readset_name)
        if parsed_args.readset_id:
            if len(parsed_args.readset_id) == 1:
                json["readset_id"] = unroll(parsed_args.readset_id[0])
            else:
                json["readset_id"] = parsed_args.readset_id

        return json

    def json_to_readset_file(self):
        readset_file = self.readset_file
        if not readset_file:
            raise ValueError("Database returned nothing, it's most likely unreachable.")
        with open(self.output_file, "w", encoding="utf-8") as out_readset_file:
            tsv_writer = csv.DictWriter(out_readset_file, delimiter='\t', fieldnames=self.READSET_HEADER)
            tsv_writer.writeheader()
            for readset_line in readset_file:
                tsv_writer.writerow(readset_line)
            logger.info(f"Readset file written to {self.output_file}")

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.readsets_samples_input = self.data()
        # When --data-file is empty
        if not self.readsets_samples_input:
            # --input-json alone
            if parsed_args.input_json:
                self.readsets_samples_input = parsed_args.input_json.read()
                parsed_args.input_json.close()
            # --sample_<name|id>/--readset_<name|id> + --endpoint
            elif (parsed_args.sample_name or parsed_args.readset_name or parsed_args.sample_id or parsed_args.readset_id) and parsed_args.endpoint:
                self.readsets_samples_input = json.dumps(self.jsonify_input(parsed_args), ensure_ascii=False, indent=4)
            else:
                raise ValueError("Either use --input-json OR --sample_<name|id>/--readset_<name|id> + --endpoint arguments.")
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
        return "Will return a Genpipes pair file in a csv format. /!\\ Either use the --input-json or the --sample/--readset + --endpoint arguments"

    def arguments(self):
        self.parser.add_argument('--output', '-o', default="pair_file.csv", help="Name of pair file returned (Default: pair_file.csv)")
        self.parser.add_argument('--sample_name', help='Sample Name to be selected', nargs='+')
        self.parser.add_argument('--readset_name', help='Readset Name to be selected', nargs='+')
        self.parser.add_argument('--sample_id', help='Sample ID to be selected', nargs='+')
        self.parser.add_argument('--readset_id', help='Readset ID to be selected', nargs='+')
        self.parser.add_argument('--endpoint', help="Endpoint in which data is located")
        self.parser.add_argument('--input-json', help="Json file with sample/readset and endpoint to be selected")

    @property
    def pair_file(self):
        '''
        Returns a list of pair lines of GenPipes of the API call for digest_pair_file
        :return:
        '''
        return self.post(f'project/{self.project_id}/digest_pair_file', data=self.readsets_samples_input)

    def jsonify_input(self, parsed_args):
        json = {
            "location_endpoint": parsed_args.endpoint
        }
        if parsed_args.sample_name:
            json["sample_name"] = list(parsed_args.sample_name)
        if parsed_args.sample_id:
            if len(parsed_args.sample_id) == 1:
                json["sample_id"] = unroll(parsed_args.sample_id[0])
            else:
                json["sample_id"] = parsed_args.sample_id
        if parsed_args.readset_name:
            json["readset_name"] = list(parsed_args.readset_name)
        if parsed_args.readset_id:
            if len(parsed_args.readset_id) == 1:
                json["readset_id"] = unroll(parsed_args.readset_id[0])
            else:
                json["readset_id"] = parsed_args.readset_id

        return json

    def json_to_pair_file(self):
        pair_file = self.pair_file
        if not pair_file:
            raise ValueError("Database returned nothing, it's most likely unreachable.")
        with open(self.output_file, "w", encoding="utf-8") as out_pair_file:
            tsv_writer = csv.DictWriter(out_pair_file, delimiter=',', fieldnames=self.PAIR_HEADER)
            # tsv_writer.writeheader()
            for pair_line in pair_file:
                tsv_writer.writerow(pair_line)
            logger.info(f"Pair file written to {self.output_file}")

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.readsets_samples_input = self.data()
        # When --data-file is empty
        if not self.readsets_samples_input:
            # --input-json alone
            if parsed_args.input_json:
                self.readsets_samples_input = parsed_args.input_json.read()
                parsed_args.input_json.close()
            # --sample_<name|id>/--readset_<name|id> + --endpoint
            elif (parsed_args.sample_name or parsed_args.readset_name or parsed_args.sample_id or parsed_args.readset_id) and parsed_args.endpoint:
                self.readsets_samples_input = json.dumps(self.jsonify_input(parsed_args), ensure_ascii=False, indent=4)
            else:
                raise ValueError("Either use --input-json OR --sample_<name|id>/--readset_<name|id> + --endpoint arguments.")
        # Checking if odd amount of sample/readset is given as input and Warn user about potential malformed file
        if json.loads(self.readsets_samples_input).get("sample_name") and not (len(json.loads(self.readsets_samples_input)["sample_name"]) % 2) == 0:
            logger.warning(f"An odd amount of 'sample_name' has been given, the pair file won't be properly formatted for GenPipes!")
        if json.loads(self.readsets_samples_input).get("sample_id") and not (len(json.loads(self.readsets_samples_input)["sample_id"]) % 2) == 0:
            logger.warning(f"An odd amount of 'sample_id' has been given, the pair file won't be properly formatted for GenPipes!")
        if json.loads(self.readsets_samples_input).get("readset_name") and not (len(json.loads(self.readsets_samples_input)["readset_name"]) % 2) == 0:
            logger.warning(f"An odd amount of 'readset_name' has been given, the pair file won't be properly formatted for GenPipes!")
        if json.loads(self.readsets_samples_input).get("readset_id") and not (len(json.loads(self.readsets_samples_input)["readset_id"]) % 2) == 0:
            logger.warning(f"An odd amount of 'readset_id' has been given, the pair file won't be properly formatted for GenPipes!")

        self.output_file = parsed_args.output
        self.json_to_pair_file()
