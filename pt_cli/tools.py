"""Module providing a sub commands to the client ot interact with the server"""

import argparse
import csv
import json
import logging
import sys
import urllib.parse
import shtab

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

class JSONDecodeError(Error):
    """Raised when JSON decoding fails."""
    def __init__(self, context, original_exception):
        message = f"Failed to decode JSON {context}: {original_exception}\n                 This is most likely not a JSON file or it's malformed."
        super().__init__(message)
        self.args = (f"{type(self).__name__}: {self.message}",)
        sys.exit(self)


def safe_json_loads(data, context=""):
    """
    Safely load JSON data, raising a custom error with context if decoding fails.
    """
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        raise JSONDecodeError(context, e) from e


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
        self.parsed_input = None
        self.output_file = None

    def help(self):
        return "Will return a Genpipes readset file in a tsv format. /!\\ Either use --input-json OR --sample_<name|id>/--readset_<name|id> + --endpoint arguments"

    def arguments(self):
        self.parser.add_argument('--output', '-o', default="readset_file.tsv", help="Name of readset file returned (Default: readset_file.tsv)")
        self.parser.add_argument('--specimen_name', help='Specimen Name to be selected', nargs='+')
        self.parser.add_argument('--sample_name', help='Sample Name to be selected', nargs='+')
        self.parser.add_argument('--readset_name', help='Readset Name to be selected', nargs='+')
        self.parser.add_argument('--specimen_id', help='Specimen ID to be selected', nargs='+')
        self.parser.add_argument('--sample_id', help='Sample ID to be selected', nargs='+')
        self.parser.add_argument('--readset_id', help='Readset ID to be selected', nargs='+')
        self.parser.add_argument('--nucleic_acid_type', help="nucleic_acid_type data type", required=False, choices=["DNA", "RNA"])
        self.parser.add_argument('--endpoint', help="Endpoint in which data is located")
        self.parser.add_argument('--input-json', help="Json file with sample/readset and endpoint to be selected", type=argparse.FileType('r')).complete = shtab.FILE

    @property
    def readset_file(self):
        '''
        :return: list of readset lines of GenPipes of the API call for digest_readset_file
        '''
        json_payload = json.dumps(self.parsed_input)
        encoded_json = urllib.parse.quote(json_payload)
        return self.get(f'project/{self.project_id}/digest_readset_file?json={encoded_json}')

    def jsonify_input(self, parsed_args):
        '''
        :return: jsonified input args
        '''
        json = {
            "location_endpoint": parsed_args.endpoint,
            "experiment_nucleic_acid_type": parsed_args.nucleic_acid_type
        }

        if parsed_args.specimen_name:
            json["specimen_name"] = list(parsed_args.specimen_name)
        if parsed_args.specimen_id:
            if len(parsed_args.specimen_id) == 1:
                json["specimen_id"] = unroll(parsed_args.specimen_id[0])
            else:
                json["specimen_id"] = parsed_args.specimen_id

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
        readset_file = readset_file["DB_ACTION_OUTPUT"]
        if not readset_file:
            sys.stdout.write("Nothing returned.")
            return
        with open(self.output_file, "w", encoding="utf-8") as out_readset_file:
            tsv_writer = csv.DictWriter(out_readset_file, delimiter='\t', fieldnames=self.READSET_HEADER)
            tsv_writer.writeheader()
            for readset_line in readset_file:
                tsv_writer.writerow(readset_line)
            logger.info(f"Readset file written to {self.output_file}")

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.parsed_input = self.data()
        # When --data-file is empty
        if not self.parsed_input:
            # --input-json alone
            if parsed_args.input_json:
                self.parsed_input = parsed_args.input_json.read()
                parsed_args.input_json.close()
            # --sample_<name|id>/--readset_<name|id> + --endpoint + --nucleic_acid_type
            elif (parsed_args.specimen_name or parsed_args.sample_name or parsed_args.readset_name or parsed_args.specimen_id or parsed_args.sample_id or parsed_args.readset_id) and parsed_args.endpoint and parsed_args.nucleic_acid_type:
                self.parsed_input = json.dumps(self.jsonify_input(parsed_args), ensure_ascii=False, indent=4)
            else:
                raise BadArgumentError("Either use --input-json OR --specimen_<name|id>/--sample_<name|id>/--readset_<name|id> + --endpoint + --nucleic_acid_type arguments.")
        self.output_file = parsed_args.output
        self.json_to_readset_file()

class PairFile(AddCMD):
    """
    PairFile is a sub-command of Digest subparser using base AddCMD class
    """
    __tool_name__ = 'pair_file'
    PAIR_HEADER = [
            "Specimen",
            "Sample_N",
            "Sample_T"
            ]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parsed_input = None
        self.output_file = None

    def help(self):
        return "Will return a Genpipes pair file in a csv format. /!\\ Either use the --input-json or the --sample/--readset + --endpoint arguments"

    def arguments(self):
        self.parser.add_argument('--output', '-o', default="pair_file.csv", help="Name of pair file returned (Default: pair_file.csv)")
        self.parser.add_argument('--specimen_name', help='Specimen Name to be selected', nargs='+')
        self.parser.add_argument('--sample_name', help='Sample Name to be selected', nargs='+')
        self.parser.add_argument('--readset_name', help='Readset Name to be selected', nargs='+')
        self.parser.add_argument('--specimen_id', help='Specimen ID to be selected', nargs='+')
        self.parser.add_argument('--sample_id', help='Sample ID to be selected', nargs='+')
        self.parser.add_argument('--readset_id', help='Readset ID to be selected', nargs='+')
        self.parser.add_argument('--nucleic_acid_type', help="nucleic_acid_type data type", required=False, choices=["DNA", "RNA"])
        self.parser.add_argument('--endpoint', help="Without effect, only here to be able to use the same command as the one used with 'pt_cli digest readset_file'")
        self.parser.add_argument('--input-json', help="Json file with sample/readset and endpoint to be selected", type=argparse.FileType('r')).complete = shtab.FILE

    @property
    def pair_file(self):
        '''
        Returns a list of pair lines of GenPipes of the API call for digest_pair_file
        :return:
        '''
        json_payload = json.dumps(self.parsed_input)
        encoded_json = urllib.parse.quote(json_payload)
        return self.get(f'project/{self.project_id}/digest_pair_file?json={encoded_json}')

    def jsonify_input(self, parsed_args):
        '''
        :return: jsonified input args
        '''
        json = {
            "location_endpoint": parsed_args.endpoint,
            "experiment_nucleic_acid_type": parsed_args.nucleic_acid_type
        }

        if parsed_args.specimen_name:
            json["specimen_name"] = list(parsed_args.specimen_name)
        if parsed_args.specimen_id:
            if len(parsed_args.specimen_id) == 1:
                json["specimen_id"] = unroll(parsed_args.specimen_id[0])
            else:
                json["specimen_id"] = parsed_args.specimen_id

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
        pair_file = pair_file["DB_ACTION_OUTPUT"]
        if not pair_file:
            sys.stdout.write("Nothing returned.")
            return
        with open(self.output_file, "w", encoding="utf-8") as out_pair_file:
            tsv_writer = csv.DictWriter(out_pair_file, delimiter=',', fieldnames=self.PAIR_HEADER)
            # tsv_writer.writeheader()
            for pair_line in pair_file:
                tsv_writer.writerow(pair_line)
            logger.info(f"Pair file written to {self.output_file}")

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.parsed_input = self.data()
        # When --data-file is empty
        if not self.parsed_input:
            # --input-json alone
            if parsed_args.input_json:
                self.parsed_input = parsed_args.input_json.read()
                parsed_args.input_json.close()
            # --sample_<name|id>/--readset_<name|id> + --endpoint + --nucleic_acid_type
            elif (parsed_args.specimen_name or parsed_args.sample_name or parsed_args.readset_name or parsed_args.specimen_id or parsed_args.sample_id or parsed_args.readset_id) and parsed_args.endpoint and parsed_args.nucleic_acid_type:
                self.parsed_input = json.dumps(self.jsonify_input(parsed_args), ensure_ascii=False, indent=4)
            else:
                raise BadArgumentError("Either use --input-json OR --specimen_<name|id>/--sample_<name|id>/--readset_<name|id> + --endpoint + --nucleic_acid_type arguments.")

        # Checking if odd amount of sample/readset is given as input and Warn user about potential malformed file
        loaded_json = safe_json_loads(self.parsed_input)
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
        self.parser.add_argument('--experiment_nucleic_acid_type', help="Experiment nucleic_acid_type characterizing the Samples/Readsets (RNA or DNA)", required=True)
        self.parser.add_argument('--endpoint', help="Endpoint in which data is located", required=True)
        self.parser.add_argument('--output', '-o', help="Name of output file (Default: terminal), formatted as Json file with sample/readset and endpoint")
        # self.parser.add_argument('--input-json', help="Json file with all parameters")

    @property
    def unanalyzed(self):
        '''
        Returns a list of pair lines of GenPipes of the API call for digest_unanalyzed
        :return:
        '''
        json_payload = json.dumps(self.parsed_input)
        encoded_json = urllib.parse.quote(json_payload)
        return self.get(f'project/{self.project_id}/digest_unanalyzed?json={encoded_json}')

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
            "experiment_nucleic_acid_type": parsed_args.experiment_nucleic_acid_type,
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
                soup = bs4.BeautifulSoup(unanalyzed, features="html5lib")
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

class Delivery(AddCMD):
    """
    Delivery is a sub-command of Digest subparser using base AddCMD class
    """
    __tool_name__ = 'delivery'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parsed_input = None
        self.output_file = None

    def help(self):
        return "Will return delivery Samples name/ID or Readsets name/ID"

    def arguments(self):
        self.parser.add_argument('--specimen_name', help='Specimen Name to be selected', nargs='+')
        self.parser.add_argument('--sample_name', help='Sample Name to be selected', nargs='+')
        self.parser.add_argument('--readset_name', help='Readset Name to be selected', nargs='+')
        self.parser.add_argument('--specimen_id', help='Specimen ID to be selected', nargs='+')
        self.parser.add_argument('--sample_id', help='Sample ID to be selected', nargs='+')
        self.parser.add_argument('--readset_id', help='Readset ID to be selected', nargs='+')
        self.parser.add_argument('--experiment_nucleic_acid_type', help="Experiment nucleic_acid_type characterizing the Samples/Readsets (RNA or DNA)", required=True)
        self.parser.add_argument('--endpoint', help="Endpoint in which data is located", required=True)
        self.parser.add_argument('--output', '-o', help="Name of output file (Default: terminal), formatted as Json file with sample/readset and endpoint")

    @property
    def delivery(self):
        '''
        Returns a list of pair lines of GenPipes of the API call for digest_delivery
        :return:
        '''
        json_payload = json.dumps(self.parsed_input)
        encoded_json = urllib.parse.quote(json_payload)
        return self.get(f'project/{self.project_id}/digest_delivery?json={encoded_json}')

    def jsonify_input(self, parsed_args):
        '''
        :return: jsonified input args
        '''
        json = {
            "location_endpoint": parsed_args.endpoint,
            "experiment_nucleic_acid_type": parsed_args.experiment_nucleic_acid_type
        }

        if parsed_args.specimen_name:
            json["specimen_name"] = list(parsed_args.specimen_name)
        if parsed_args.specimen_id:
            if len(parsed_args.specimen_id) == 1:
                json["specimen_id"] = unroll(parsed_args.specimen_id[0])
            else:
                json["specimen_id"] = parsed_args.specimen_id

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

    def json_to_delivery(self):
        """
        Writes the output file/prints to terminal
        """
        delivery = self.delivery
        if not self.output_file:
            if isinstance(delivery, str):
                soup = bs4.BeautifulSoup(delivery, features="html5lib")
                return sys.stdout.write(soup.get_text())
            # else case, not explicitely written
            return sys.stdout.write(json.dumps(delivery["DB_ACTION_OUTPUT"]))
        if not delivery:
            raise EmptyGetError
        with open(self.output_file, "w", encoding="utf-8") as out_pair_file:
            json.dump(delivery["DB_ACTION_OUTPUT"], out_pair_file, ensure_ascii=False, indent=4)
            logger.info(f"Delivery file written to {self.output_file}")

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.parsed_input = self.data()
        # When --data-file is empty
        if not self.parsed_input:
            if parsed_args.specimen_name or parsed_args.sample_name or parsed_args.readset_name or parsed_args.specimen_id or parsed_args.sample_id or parsed_args.readset_id:
                self.parsed_input = self.jsonify_input(parsed_args)
            else:
                raise BadArgumentError("Use at least one of the following --specimen_<name|id>/--sample_<name|id>/--readset_<name|id> argument.")

        self.output_file = parsed_args.output
        self.json_to_delivery()

class RunProcessing(AddCMD):
    """
    RunProcessing is a sub-command of Ingest subparser using base AddCMD class
    """
    __tool_name__ = 'run_processing'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.run_processing_input = None

    def help(self):
        return "Will push Run Processing data into the database"

    def arguments(self):
        self.parser.add_argument('--input-json', help="Json file containing all information to add data from Run Processing into the database", type=argparse.FileType('r')).complete = shtab.FILE

    @property
    def run_processing(self):
        '''
        :return: list of readset lines of GenPipes of the API call for ingest_run_processing
        '''
        return self.post(f'project/{self.project_id}/ingest_run_processing', data=self.run_processing_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.run_processing_input = self.data()
        # When --data-file is empty
        if not self.run_processing_input and parsed_args.input_json:
            self.run_processing_input = parsed_args.input_json.read()
            file_name = parsed_args.input_json.name
            parsed_args.input_json.close()
            payload = safe_json_loads(self.run_processing_input)
            payload["_source_file"] = file_name
            self.run_processing_input = json.dumps(payload)

        if not self.run_processing_input:
            raise BadArgumentError

        response = self.run_processing
        if isinstance(response, str) and response.startswith("Welcome"):
            pass
        else:
            sys.stdout.write("\n".join([json.dumps(i) for i in response["DB_ACTION_OUTPUT"]]))

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
        self.parser.add_argument('--input-json', help="Json file containing all information to add data from a Transfer into the database", type=argparse.FileType('r')).complete = shtab.FILE

    @property
    def transfer(self):
        '''
        :return: list of readset lines of GenPipes of the API call for ingest_transfer
        '''
        return self.post(f'project/{self.project_id}/ingest_transfer', data=self.transfer_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.transfer_input = self.data()
        # When --data-file is empty
        if not self.transfer_input and parsed_args.input_json:
            self.transfer_input = parsed_args.input_json.read()
            file_name = parsed_args.input_json.name
            parsed_args.input_json.close()
            payload = safe_json_loads(self.transfer_input)
            payload["_source_file"] = file_name
            self.transfer_input = json.dumps(payload)
        if not self.transfer_input:
            raise BadArgumentError

        response = self.transfer
        if isinstance(response, str) and response.startswith("Welcome"):
            pass
        else:
            sys.stdout.write("\n".join([json.dumps(i) for i in response["DB_ACTION_OUTPUT"]]))

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
        self.parser.add_argument('--input-json', help="Json file containing all information to add a GenPipes analysis into the database", type=argparse.FileType('r')).complete = shtab.FILE

    @property
    def genpipes(self):
        '''
        :return: list of readset lines of GenPipes of the API call for ingest_genpipes
        '''
        return self.post(f'project/{self.project_id}/ingest_genpipes', data=self.genpipes_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.genpipes_input = self.data()
        # When --data-file is empty
        if not self.genpipes_input and parsed_args.input_json:
            self.genpipes_input = parsed_args.input_json.read()
            file_name = parsed_args.input_json.name
            parsed_args.input_json.close()
            payload = safe_json_loads(self.genpipes_input)
            payload["_source_file"] = file_name
            self.genpipes_input = json.dumps(payload)
        if not self.genpipes_input:
            raise BadArgumentError

        response = self.genpipes
        if isinstance(response, str) and response.startswith("Welcome"):
            pass
        else:
            sys.stdout.write("\n".join([json.dumps(i) for i in response["DB_ACTION_OUTPUT"]]))

class DeliveryIngest(AddCMD):
    """
    DeliveryIngest is a sub-command of Ingest subparser using base AddCMD class
    """
    __tool_name__ = 'delivery'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delivery_input = None

    def help(self):
        return "Will push a Delivery of data into the database"

    def arguments(self):
        self.parser.add_argument('--input-json', help="Json file containing all information to add data from a Delivery into the database", type=argparse.FileType('r')).complete = shtab.FILE
        self.parser.add_argument('--delete', action='store_true', default=True, help="By default, delivery will delete the files from their original location after transfer. If you want to keep the original files, set this flag to False.")

    @property
    def delivery(self):
        '''
        :return: list of readset lines of GenPipes of the API call for ingest_delivery
        '''
        return self.post(f'project/{self.project_id}/ingest_delivery', data=self.delivery_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.delivery_input = self.data()
        # When --data-file is empty
        if not self.delivery_input and parsed_args.input_json:
            self.delivery_input = parsed_args.input_json.read()
            file_name = parsed_args.input_json.name
            parsed_args.input_json.close()
            payload = safe_json_loads(self.delivery_input)
            payload["_source_file"] = file_name
            self.delivery_input = json.dumps(payload)
        if not self.delivery_input:
            raise BadArgumentError

        self.delivery_input = safe_json_loads(self.delivery_input)
        self.delivery_input["delete"] = parsed_args.delete
        self.delivery_input = json.dumps(self.delivery_input, ensure_ascii=False, indent=4)

        response = self.delivery
        if isinstance(response, str) and response.startswith("Welcome"):
            pass
        else:
            sys.stdout.write("\n".join([json.dumps(i) for i in response["DB_ACTION_OUTPUT"]]))

class Edit(AddCMD):
    """
    Edit is a sub-command base AddCMD class
    """
    __tool_name__ = 'edit'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.edit_input = None

    def help(self):
        return "Will Edit an existing entry of the database. /!\\ This action is not reversible."

    def arguments(self):
        self.parser.add_argument('--input-json', help="Json file containing all information to be edited on the database", type=argparse.FileType('r')).complete = shtab.FILE
        self.parser.add_argument('--dry_run', action='store_true', default=False, help="If set, will only print the entries that will be curated without actually curating them.")

    @property
    def edit(self):
        '''
        :return: list of readset lines of GenPipes of the API call for ingest_edit
        '''
        return self.post('modification/edit', data=self.edit_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.edit_input = self.data()
        # When --data-file is empty
        if not self.edit_input and parsed_args.input_json:
            self.edit_input = parsed_args.input_json.read()
            parsed_args.input_json.close()
        if not self.edit_input:
            raise BadArgumentError

        # Add dry_run flag if set
        if parsed_args.dry_run:
            self.edit_input = safe_json_loads(self.edit_input)
            self.edit_input["dry_run"] = True
            self.edit_input = json.dumps(self.edit_input, ensure_ascii=False, indent=4)

        response = self.edit
        if isinstance(response, str) and response.startswith("Welcome"):
            pass
        else:
            sys.stdout.write("\n".join(response["DB_ACTION_OUTPUT"]))

class Delete(AddCMD):
    """
    Delete is a sub-command base AddCMD class
    """
    __tool_name__ = 'delete'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delete_input = None

    def help(self):
        return "Will Delete an existing entry of the database: set deleted flag to True"

    def arguments(self):
        self.parser.add_argument('--input-json', help="Json file containing all information to be deleted on the database", type=argparse.FileType('r')).complete = shtab.FILE
        self.parser.add_argument('--dry_run', action='store_true', default=False, help="If set, will only print the entries that will be curated without actually curating them.")
        self.parser.add_argument('--cascade_down', help="Cascade delete, will delete all children of the entry and orphan", action='store_true', default=False)
        self.parser.add_argument('--cascade_up', help="Cascade delete, will delete all parents of the entry and orphan", action='store_true', default=False)
        self.parser.add_argument('--cascade', help="Cascade delete, will delete all parents and children of the entry and orphan", action='store_true', default=False)

    @property
    def delete(self):
        '''
        :return: list of readset lines of GenPipes of the API call for ingest_delete
        '''
        return self.post('modification/delete', data=self.delete_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.delete_input = self.data()
        # When --data-file is empty
        if not self.delete_input and parsed_args.input_json:
            self.delete_input = parsed_args.input_json.read()
            parsed_args.input_json.close()
        if not self.delete_input:
            raise BadArgumentError

        # Add dry_run flag if set
        if parsed_args.dry_run:
            self.delete_input = safe_json_loads(self.delete_input)
            self.delete_input["dry_run"] = True
            self.delete_input = json.dumps(self.delete_input, ensure_ascii=False, indent=4)

        # Adding cascade options to the input
        if parsed_args.cascade_down:
            self.delete_input = safe_json_loads(self.delete_input)
            self.delete_input["cascade_down"] = True
            self.delete_input = json.dumps(self.delete_input, ensure_ascii=False, indent=4)
        elif parsed_args.cascade_up:
            self.delete_input = safe_json_loads(self.delete_input)
            self.delete_input["cascade_up"] = True
            self.delete_input = json.dumps(self.delete_input, ensure_ascii=False, indent=4)
        elif parsed_args.cascade:
            self.delete_input = safe_json_loads(self.delete_input)
            self.delete_input["cascade"] = True
            self.delete_input = json.dumps(self.delete_input, ensure_ascii=False, indent=4)

        response = self.delete
        if isinstance(response, str) and response.startswith("Welcome"):
            pass
        else:
            sys.stdout.write("\n".join(response["DB_ACTION_OUTPUT"]))

class UnDelete(AddCMD):
    """
    UnDelete is a sub-command base AddCMD class
    """
    __tool_name__ = 'undelete'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.undelete_input = None

    def help(self):
        return "Will UnDelete an existing entry of the database: set deleted flag to False"

    def arguments(self):
        self.parser.add_argument('--input-json', help="Json file containing all information to be undeleted on the database", type=argparse.FileType('r')).complete = shtab.FILE
        self.parser.add_argument('--dry_run', action='store_true', default=False, help="If set, will only print the entries that will be curated without actually curating them.")
        self.parser.add_argument('--cascade_down', help="Cascade undelete, will undelete all children of the entry and orphan", action='store_true', default=False)
        self.parser.add_argument('--cascade_up', help="Cascade undelete, will undelete all parents of the entry and orphan", action='store_true', default=False)
        self.parser.add_argument('--cascade', help="Cascade undelete, will undelete all parents and children of the entry and orphan", action='store_true', default=False)

    @property
    def undelete(self):
        '''
        :return: list of readset lines of GenPipes of the API call for ingest_undelete
        '''
        return self.post('modification/undelete', data=self.undelete_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.undelete_input = self.data()
        # When --data-file is empty
        if not self.undelete_input and parsed_args.input_json:
            self.undelete_input = parsed_args.input_json.read()
            parsed_args.input_json.close()
        if not self.undelete_input:
            raise BadArgumentError

        # Add dry_run flag if set
        if parsed_args.dry_run:
            self.undelete_input = safe_json_loads(self.undelete_input)
            self.undelete_input["dry_run"] = True
            self.undelete_input = json.dumps(self.undelete_input, ensure_ascii=False, indent=4)

        # Adding cascade options to the input
        if parsed_args.cascade_down:
            self.undelete_input = safe_json_loads(self.undelete_input)
            self.undelete_input["cascade_down"] = True
            self.undelete_input = json.dumps(self.undelete_input, ensure_ascii=False, indent=4)
        elif parsed_args.cascade_up:
            self.undelete_input = safe_json_loads(self.undelete_input)
            self.undelete_input["cascade_up"] = True
            self.undelete_input = json.dumps(self.undelete_input, ensure_ascii=False, indent=4)
        elif parsed_args.cascade:
            self.undelete_input = safe_json_loads(self.undelete_input)
            self.undelete_input["cascade"] = True
            self.undelete_input = json.dumps(self.undelete_input, ensure_ascii=False, indent=4)

        response = self.undelete
        if isinstance(response, str) and response.startswith("Welcome"):
            pass
        else:
            sys.stdout.write("\n".join(response["DB_ACTION_OUTPUT"]))

class Deprecate(AddCMD):
    """
    Deprecate is a sub-command base AddCMD class
    """
    __tool_name__ = 'deprecate'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.deprecate_input = None

    def help(self):
        return "Will Deprecate an existing entry of the database: set deprecated flag to True"

    def arguments(self):
        self.parser.add_argument('--input-json', help="Json file containing all information to be deprecated on the database", type=argparse.FileType('r')).complete = shtab.FILE
        self.parser.add_argument('--dry_run', action='store_true', default=False, help="If set, will only print the entries that will be curated without actually curating them.")
        self.parser.add_argument('--cascade_down', help="Cascade undelete, will undelete all children of the entry and orphan", action='store_true', default=False)
        self.parser.add_argument('--cascade_up', help="Cascade undelete, will undelete all parents of the entry and orphan", action='store_true', default=False)
        self.parser.add_argument('--cascade', help="Cascade undelete, will undelete all parents and children of the entry and orphan", action='store_true', default=False)

    @property
    def deprecate(self):
        '''
        :return: list of readset lines of GenPipes of the API call for ingest_deprecate
        '''
        return self.post('modification/deprecate', data=self.deprecate_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.deprecate_input = self.data()
        # When --data-file is empty
        if not self.deprecate_input and parsed_args.input_json:
            self.deprecate_input = parsed_args.input_json.read()
            parsed_args.input_json.close()
        if not self.deprecate_input:
            raise BadArgumentError

        # Add dry_run flag if set
        if parsed_args.dry_run:
            self.deprecate_input = safe_json_loads(self.deprecate_input)
            self.deprecate_input["dry_run"] = True
            self.deprecate_input = json.dumps(self.deprecate_input, ensure_ascii=False, indent=4)

        # Adding cascade options to the input
        if parsed_args.cascade_down:
            self.deprecate_input = safe_json_loads(self.deprecate_input)
            self.deprecate_input["cascade_down"] = True
            self.deprecate_input = json.dumps(self.deprecate_input, ensure_ascii=False, indent=4)
        elif parsed_args.cascade_up:
            self.deprecate_input = safe_json_loads(self.deprecate_input)
            self.deprecate_input["cascade_up"] = True
            self.deprecate_input = json.dumps(self.deprecate_input, ensure_ascii=False, indent=4)
        elif parsed_args.cascade:
            self.deprecate_input = safe_json_loads(self.deprecate_input)
            self.deprecate_input["cascade"] = True
            self.deprecate_input = json.dumps(self.deprecate_input, ensure_ascii=False, indent=4)

        response = self.deprecate
        if isinstance(response, str) and response.startswith("Welcome"):
            pass
        else:
            sys.stdout.write("\n".join(response["DB_ACTION_OUTPUT"]))

class UnDeprecate(AddCMD):
    """
    UnDeprecate is a sub-command base AddCMD class
    """
    __tool_name__ = 'undeprecate'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.undeprecate_input = None

    def help(self):
        return "Will UnDeprecate an existing entry of the database: set deprecated flag to False"

    def arguments(self):
        self.parser.add_argument('--input-json', help="Json file containing all information to be undeprecated on the database", type=argparse.FileType('r')).complete = shtab.FILE
        self.parser.add_argument('--dry_run', action='store_true', default=False, help="If set, will only print the entries that will be curated without actually curating them.")
        self.parser.add_argument('--cascade_down', help="Cascade undelete, will undelete all children of the entry and orphan", action='store_true', default=False)
        self.parser.add_argument('--cascade_up', help="Cascade undelete, will undelete all parents of the entry and orphan", action='store_true', default=False)
        self.parser.add_argument('--cascade', help="Cascade undelete, will undelete all parents and children of the entry and orphan", action='store_true', default=False)

    @property
    def undeprecate(self):
        '''
        :return: list of readset lines of GenPipes of the API call for ingest_undeprecate
        '''
        return self.post('modification/undeprecate', data=self.undeprecate_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.undeprecate_input = self.data()
        # When --data-file is empty
        if not self.undeprecate_input and parsed_args.input_json:
            self.undeprecate_input = parsed_args.input_json.read()
            parsed_args.input_json.close()
        if not self.undeprecate_input:
            raise BadArgumentError

        # Add dry_run flag if set
        if parsed_args.dry_run:
            self.undeprecate_input = safe_json_loads(self.undeprecate_input)
            self.undeprecate_input["dry_run"] = True
            self.undeprecate_input = json.dumps(self.undeprecate_input, ensure_ascii=False, indent=4)

        # Adding cascade options to the input
        if parsed_args.cascade_down:
            self.undeprecate_input = safe_json_loads(self.undeprecate_input)
            self.undeprecate_input["cascade_down"] = True
            self.undeprecate_input = json.dumps(self.undeprecate_input, ensure_ascii=False, indent=4)
        elif parsed_args.cascade_up:
            self.undeprecate_input = safe_json_loads(self.undeprecate_input)
            self.undeprecate_input["cascade_up"] = True
            self.undeprecate_input = json.dumps(self.undeprecate_input, ensure_ascii=False, indent=4)
        elif parsed_args.cascade:
            self.undeprecate_input = safe_json_loads(self.undeprecate_input)
            self.undeprecate_input["cascade"] = True
            self.undeprecate_input = json.dumps(self.undeprecate_input, ensure_ascii=False, indent=4)

        response = self.undeprecate
        if isinstance(response, str) and response.startswith("Welcome"):
            pass
        else:
            sys.stdout.write("\n".join(response["DB_ACTION_OUTPUT"]))

class Curate(AddCMD):
    """
    Curate is a sub-command base AddCMD class
    """
    __tool_name__ = 'curate'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.curate_input = None

    def help(self):
        return "Will Curate an existing entry of the database: delete an entry. /!\\ This action is not reversible."

    def arguments(self):
        self.parser.add_argument('--input-json', help="Json file containing all information to be curated from the database", type=argparse.FileType('r')).complete = shtab.FILE
        self.parser.add_argument('--dry_run', action='store_true', default=False, help="If set, will only print the entries that will be curated without actually curating them.")
        self.parser.add_argument('--cascade_down', help="Cascade undelete, will undelete all children of the entry and orphan", action='store_true', default=False)
        self.parser.add_argument('--cascade_up', help="Cascade undelete, will undelete all parents of the entry and orphan", action='store_true', default=False)
        self.parser.add_argument('--cascade', help="Cascade undelete, will undelete all parents and children of the entry and orphan", action='store_true', default=False)

    @property
    def curate(self):
        '''
        :return: list of readset lines of GenPipes of the API call for ingest_curate
        '''
        return self.post('modification/curate', data=self.curate_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        # Dev case when using --data-file
        self.curate_input = self.data()
        # When --data-file is empty
        if not self.curate_input and parsed_args.input_json:
            self.curate_input = parsed_args.input_json.read()
            parsed_args.input_json.close()

        # Ensure curate_input is not empty
        if not self.curate_input:
            raise BadArgumentError

        # Add dry_run flag if set
        if parsed_args.dry_run:
            self.curate_input = safe_json_loads(self.curate_input)
            self.curate_input["dry_run"] = True
            self.curate_input = json.dumps(self.curate_input, ensure_ascii=False, indent=4)

        # Adding cascade options to the input
        if parsed_args.cascade_down:
            self.curate_input = safe_json_loads(self.curate_input)
            self.curate_input["cascade_down"] = True
            self.curate_input = json.dumps(self.curate_input, ensure_ascii=False, indent=4)
        elif parsed_args.cascade_up:
            self.curate_input = safe_json_loads(self.curate_input)
            self.curate_input["cascade_up"] = True
            self.curate_input = json.dumps(self.curate_input, ensure_ascii=False, indent=4)
        elif parsed_args.cascade:
            self.curate_input = safe_json_loads(self.curate_input)
            self.curate_input["cascade"] = True
            self.curate_input = json.dumps(self.curate_input, ensure_ascii=False, indent=4)

        response = self.curate
        if isinstance(response, str) and response.startswith("Welcome"):
            pass
        else:
            sys.stdout.write("\n".join(response["DB_ACTION_OUTPUT"]))
