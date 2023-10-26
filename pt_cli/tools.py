"""Module providing a sub commands to the client ot interact with the server"""

import argparse
import csv
import json
import logging
import sys

import bs4

logger = logging.getLogger(__name__)

class Error(Exception):
    """docstring for Error"""
    def __init__(self, message):
        self.message = message

class BadArgumentError(Error):
    """docstring for BadArgumentError"""
    def __init__(self, message=None):
        super().__init__(message)
        if message:
            self.message = message
        else:
            self.message = "Either use --input-json OR general option --data/--data-file from pt_cli"
        self.args = (f"{type(self).__name__}: {self.message}",)
        sys.exit(self)

class EmptyGetError(Error):
    """docstring for EmptyGetError"""
    def __init__(self, message=None):
        super().__init__(message)
        if message:
            self.message = message
        else:
            self.message = "Database returned nothing, it's most likely unreachable"
        self.args = (f"{type(self).__name__}: {self.message}",)
        sys.exit(self)

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

class Digest:
    """
    Digest is a subparser of the client in which all digestion sub-commands will be added.
    """
    __tool_name__ = 'digest'

    def __init__(self, subparser=argparse.ArgumentParser().add_subparsers()):
        self.subparser = subparser.add_parser(self.__tool_name__, help=self.help(), add_help=True).add_subparsers()

    def help(self):
        """
        :return: the tool help string
        """
        return f"All {self.__tool_name__} sub commands, those encapsulate all operation pulling information from the database. Use 'pt_cli {self.__tool_name__} --help' to see more details."

class Ingest:
    """
    Ingest is a subparser of the client in which all digestion sub-commands will be added.
    """
    __tool_name__ = 'ingest'

    def __init__(self, subparser=argparse.ArgumentParser().add_subparsers()):
        self.subparser = subparser.add_parser(self.__tool_name__, help=self.help(), add_help=True).add_subparsers()

    def help(self):
        """
        :return: the tool help string
        """
        return f"All {self.__tool_name__} sub commands, those encapsulate all operation pushing information into the database. Use 'pt_cli {self.__tool_name__} --help' to see more details."


class AddCMD:
    """
    AddCMD is the basic class to write pt_cli tools.
    To create a new subcommand, create a child class 
    and write help(), arguments() and func() methods 
    """
    __tool_name__ = 'tool_name'

    _POSTED_DATA = None

    def __init__(self, connection_obj, subparser=argparse.ArgumentParser().add_subparsers()):
        """
        :param connection_obj: helps to Connect and identify yourself to the Database api
        :param subparser: arguments that triggers the tool, The default is set here to help the autocomplete
        """
        self.connection_obj = connection_obj
        self.subparser = subparser
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
                raise BadArgumentError(f'Data inputs is needed for the "{self.__tool_name__}" subcommand')

        return self._POSTED_DATA

    def post(self, path, data):
        """
        :return: the post query on the server
        """
        return self.connection_obj.post(path, data=data)

    def get(self, path):
        """
        :return: the get query on the server
        """
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
    """
    ReadsetFile is a sub-command of Digest subparser using base AddCMD class
    """
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
        :return: list of readset lines of GenPipes of the API call for digest_readset_file
        '''
        return self.post(f'project/{self.project_id}/digest_readset_file', data=self.readsets_samples_input)

    def jsonify_input(self, parsed_args):
        '''
        :return: jsonified input args
        '''
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
        """
        Writes the output file
        """
        readset_file = self.readset_file
        if not readset_file:
            raise EmptyGetError
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
                raise BadArgumentError("Either use --input-json OR --sample_<name|id>/--readset_<name|id> + --endpoint arguments.")
        self.output_file = parsed_args.output
        self.json_to_readset_file()

class PairFile(AddCMD):
    """
    PairFile is a sub-command of Digest subparser using base AddCMD class
    """
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
        '''
        :return: jsonified input args
        '''
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
        """
        Writes the pair file
        """
        pair_file = self.pair_file
        if not pair_file:
            raise EmptyGetError
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
                raise BadArgumentError("Either use --input-json OR --sample_<name|id>/--readset_<name|id> + --endpoint arguments.")

        # Checking if odd amount of sample/readset is given as input and Warn user about potential malformed file
        loaded_json = json.loads(self.readsets_samples_input)
        if loaded_json.get("sample_name") and not (len(loaded_json["sample_name"]) % 2) == 0:
            logger.warning("An odd amount of 'sample_name' has been given, the pair file won't be properly formatted for GenPipes!")
        if loaded_json.get("sample_id") and not (len(loaded_json["sample_id"]) % 2) == 0:
            logger.warning("An odd amount of 'sample_id' has been given, the pair file won't be properly formatted for GenPipes!")
        if loaded_json.get("readset_name") and not (len(loaded_json["readset_name"]) % 2) == 0:
            logger.warning("An odd amount of 'readset_name' has been given, the pair file won't be properly formatted for GenPipes!")
        if loaded_json.get("readset_id") and not (len(loaded_json["readset_id"]) % 2) == 0:
            logger.warning("An odd amount of 'readset_id' has been given, the pair file won't be properly formatted for GenPipes!")

        self.output_file = parsed_args.output
        self.json_to_pair_file()

class Unanalyzed(AddCMD):
    """
    Unanalyzed is a sub-command of Digest subparser using base AddCMD class
    """
    __tool_name__ = 'unanalyzed'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parsed_input = None
        self.output_file = None

    def help(self):
        return "Will return unanalyzed Samples name/ID or Readsets name/ID"

    def arguments(self):
        self.parser.add_argument('--sample_name', help='Sample Name will be selected', action='store_true', default=False)
        self.parser.add_argument('--readset_name', help='Readset Name will be selected', action='store_true', default=False)
        self.parser.add_argument('--sample_id', help='Sample ID will be selected', action='store_true', default=False)
        self.parser.add_argument('--readset_id', help='Readset ID will be selected', action='store_true', default=False)
        self.parser.add_argument('--run_name', help="Run Name in which Samples/Readsets are", required=False, default=None)
        self.parser.add_argument('--run_id', help="Run ID in which Samples/Readsets are", required=False, default=None)
        self.parser.add_argument('--experiment_sequencing_technology', help="Experiment Sequencing_Technology in which Samples/Readsets are", required=False, default=None)
        self.parser.add_argument('--endpoint', help="Endpoint in which data is located", required=True)
        self.parser.add_argument('--output', '-o', help="Name of output file (Default: terminal), formatted as Json file with sample/readset and endpoint")
        # self.parser.add_argument('--input-json', help="Json file with all parameters")

    @property
    def unanalyzed(self):
        '''
        Returns a list of pair lines of GenPipes of the API call for digest_unanalyzed
        :return:
        '''
        return self.post(f'project/{self.project_id}/digest_unanalyzed', data=self.parsed_input)

    def jsonify_input(self, parsed_args):
        '''
        :return: jsonified input args
        '''
        json = {
            "sample_name": parsed_args.sample_name,
            "sample_id": parsed_args.sample_id,
            "readset_name": parsed_args.readset_name,
            "readset_id": parsed_args.readset_id,
            "run_name": parsed_args.run_name,
            "run_id": parsed_args.run_id,
            "experiment_sequencing_technology": parsed_args.experiment_sequencing_technology,
            "location_endpoint": parsed_args.endpoint,
        }

        return json

    def json_to_unanalyzed(self):
        """
        Writes the output file/prints to terminal
        """
        unanalyzed = self.unanalyzed
        if not self.output_file:
            if isinstance(unanalyzed, str):
                soup = bs4.BeautifulSoup(unanalyzed, features="lxml")
                return sys.stdout.write(soup.get_text())
            # else case, not explicitely written
            return sys.stdout.write(json.dumps(unanalyzed))
        if not unanalyzed:
            raise EmptyGetError
        with open(self.output_file, "w", encoding="utf-8") as out_pair_file:
            json.dump(unanalyzed, out_pair_file, ensure_ascii=False, indent=4)
            logger.info(f"Unanalyzed file written to {self.output_file}")

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.parsed_input = self.data()
        # When --data-file is empty
        if not self.parsed_input:
            if parsed_args.sample_name or parsed_args.readset_name or parsed_args.sample_id or parsed_args.readset_id:
                self.parsed_input = json.dumps(self.jsonify_input(parsed_args), ensure_ascii=False, indent=4)
            else:
                raise BadArgumentError("Use at least one of the following --sample_<name|id>/--readset_<name|id> argument.")

        self.output_file = parsed_args.output
        self.json_to_unanalyzed()

class RunProcessing(AddCMD):
    """
    RunProcessing is a sub-command of Ingest subparser using base AddCMD class
    """
    __tool_name__ = 'run_processing'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.run_processing_input = None
        self.output_file = None

    def help(self):
        return "Will push Run Processing data into the database"

    def arguments(self):
        self.parser.add_argument('--input-json', help="Json file containing all information to add data from Run Processing into the database")

    @property
    def run_processing(self):
        '''
        :return: list of readset lines of GenPipes of the API call for digest_readset_file
        '''
        return self.post(f'project/{self.project_id}/ingest_run_processing', data=self.run_processing_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.run_processing_input = self.data()
        # When --data-file is empty
        if not self.run_processing_input and parsed_args.input_json:
            self.run_processing_input = parsed_args.input_json.read()
            parsed_args.input_json.close()
        if not self.run_processing_input:
            raise BadArgumentError

        self.run_processing()

class Transfer(AddCMD):
    """
    Transfer is a sub-command of Ingest subparser using base AddCMD class
    """
    __tool_name__ = 'transfer'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transfer_input = None
        self.output_file = None

    def help(self):
        return "Will push a Transfer of data (copy, rsync, mv, etc) into the database"

    def arguments(self):
        self.parser.add_argument('--input-json', help="Json file containing all information to add data from a Transfer into the database")

    @property
    def transfer(self):
        '''
        :return: list of readset lines of GenPipes of the API call for digest_readset_file
        '''
        return self.post(f'project/{self.project_id}/ingest_transfer', data=self.transfer_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.transfer_input = self.data()
        # When --data-file is empty
        if not self.transfer_input and parsed_args.input_json:
            self.transfer_input = parsed_args.input_json.read()
            parsed_args.input_json.close()
        if not self.transfer_input:
            raise BadArgumentError

        self.transfer()

class GenPipes(AddCMD):
    """
    GenPipes is a sub-command of Ingest subparser using base AddCMD class
    """
    __tool_name__ = 'genpipes'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.genpipes_input = None
        self.output_file = None

    def help(self):
        return "Will push a GenPipes analysis into the database"

    def arguments(self):
        self.parser.add_argument('--input-json', help="Json file containing all information to add a GenPipes analysis into the database")

    @property
    def genpipes(self):
        '''
        :return: list of readset lines of GenPipes of the API call for digest_readset_file
        '''
        return self.post(f'project/{self.project_id}/ingest_genpipes', data=self.genpipes_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.genpipes_input = self.data()
        # When --data-file is empty
        if not self.genpipes_input and parsed_args.input_json:
            self.genpipes_input = parsed_args.input_json.read()
            parsed_args.input_json.close()
        if not self.genpipes_input:
            raise BadArgumentError

        self.genpipes()
