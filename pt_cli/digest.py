import argparse
import csv
import json
import logging
import sys
import urllib.parse

import shtab
import bs4

from pt_cli.tools import AddCMD, BadArgumentError, EmptyGetError, unroll

logger = logging.getLogger(__name__)


class Digest:
    """
    Digest is a subparser of the client in which all digestion sub-commands are added.
    """

    __tool_name__ = 'digest'

    def __init__(self, subparser=argparse.ArgumentParser().add_subparsers()):
        self.subparser = subparser.add_parser(self.__tool_name__, help=self.help(), add_help=True).add_subparsers()

    def help(self):
        return (
            f"All {self.__tool_name__} sub commands, those encapsulate all operation pulling "
            f"information from the database. Use 'pt_cli {self.__tool_name__} --help' to see more details."
        )


def register_digest_commands(subparser, connection_obj):
    digest_subparser = Digest(subparser).subparser
    ReadsetFile(connection_obj=connection_obj, subparser=digest_subparser)
    PairFile(connection_obj=connection_obj, subparser=digest_subparser)
    Unanalyzed(connection_obj=connection_obj, subparser=digest_subparser)
    Delivery(connection_obj=connection_obj, subparser=digest_subparser)


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
        self.parser.add_argument('--input-json', help="Json file with sample/readset and endpoint to be selected", type=argparse.FileType('r')).complete = shtab.FILE  # type: ignore[attr-defined]

    @property
    def readset_file(self):
        if isinstance(self.parsed_input, str):
            parsed_dict = json.loads(self.parsed_input)
        else:
            parsed_dict = self.parsed_input
        json_payload = json.dumps(parsed_dict)
        encoded_json = urllib.parse.quote(json_payload)
        return self.get(f'project/{self.project_id}/digest_readset_file?json={encoded_json}')

    def jsonify_input(self, parsed_args):
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
        readset_file = self.readset_file
        if not readset_file:
            raise EmptyGetError
        readset_file = readset_file["DB_ACTION_OUTPUT"]
        if not readset_file:
            sys.stdout.write("Nothing returned.")
            return
        if self.output_file is None:
            raise BadArgumentError("Missing output path")
        with open(self.output_file, "w", encoding="utf-8") as out_readset_file:
            tsv_writer = csv.DictWriter(out_readset_file, delimiter='\t', fieldnames=self.READSET_HEADER)
            tsv_writer.writeheader()
            for readset_line in readset_file:
                tsv_writer.writerow(readset_line)
            logger.info(f"Readset file written to {self.output_file}")

    def func(self, parsed_args):
        super().func(parsed_args)
        self.parsed_input = self.data()
        if not self.parsed_input:
            if parsed_args.input_json:
                self.parsed_input = parsed_args.input_json.read()
                parsed_args.input_json.close()
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
        self.parser.add_argument('--input-json', help="Json file with sample/readset and endpoint to be selected", type=argparse.FileType('r')).complete = shtab.FILE  # type: ignore[attr-defined]

    @property
    def pair_file(self):
        if isinstance(self.parsed_input, str):
            parsed_dict = json.loads(self.parsed_input)
        else:
            parsed_dict = self.parsed_input
        json_payload = json.dumps(parsed_dict)
        encoded_json = urllib.parse.quote(json_payload)
        return self.get(f'project/{self.project_id}/digest_pair_file?json={encoded_json}')

    def jsonify_input(self, parsed_args):
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
        pair_file = self.pair_file
        if not pair_file:
            raise EmptyGetError
        pair_file = pair_file["DB_ACTION_OUTPUT"]
        if not pair_file:
            sys.stdout.write("Nothing returned.")
            return
        if self.output_file is None:
            raise BadArgumentError("Missing output path")
        with open(self.output_file, "w", encoding="utf-8") as out_pair_file:
            tsv_writer = csv.DictWriter(out_pair_file, delimiter=',', fieldnames=self.PAIR_HEADER)
            for pair_line in pair_file:
                tsv_writer.writerow(pair_line)
            logger.info(f"Pair file written to {self.output_file}")

    def func(self, parsed_args):
        super().func(parsed_args)
        self.parsed_input = self.data()
        if not self.parsed_input:
            if parsed_args.input_json:
                self.parsed_input = parsed_args.input_json.read()
                parsed_args.input_json.close()
            elif (parsed_args.specimen_name or parsed_args.sample_name or parsed_args.readset_name or parsed_args.specimen_id or parsed_args.sample_id or parsed_args.readset_id) and parsed_args.endpoint and parsed_args.nucleic_acid_type:
                self.parsed_input = json.dumps(self.jsonify_input(parsed_args), ensure_ascii=False, indent=4)
            else:
                raise BadArgumentError("Either use --input-json OR --specimen_<name|id>/--sample_<name|id>/--readset_<name|id> + --endpoint + --nucleic_acid_type arguments.")

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

    @property
    def unanalyzed(self):
        if isinstance(self.parsed_input, str):
            parsed_dict = json.loads(self.parsed_input)
        else:
            parsed_dict = self.parsed_input
        json_payload = json.dumps(parsed_dict)
        encoded_json = urllib.parse.quote(json_payload)
        return self.get(f'project/{self.project_id}/digest_unanalyzed?json={encoded_json}')

    def jsonify_input(self, parsed_args):
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
        unanalyzed = self.unanalyzed
        if not self.output_file:
            if isinstance(unanalyzed, str):
                soup = bs4.BeautifulSoup(unanalyzed, features="html5lib")
                return sys.stdout.write(soup.get_text())
            return sys.stdout.write(json.dumps(unanalyzed))
        if not unanalyzed:
            raise EmptyGetError
        with open(self.output_file, "w", encoding="utf-8") as out_pair_file:
            json.dump(unanalyzed, out_pair_file, ensure_ascii=False, indent=4)
            logger.info(f"Unanalyzed file written to {self.output_file}")

    def func(self, parsed_args):
        super().func(parsed_args)
        self.parsed_input = self.data()
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
        if isinstance(self.parsed_input, str):
            parsed_dict = json.loads(self.parsed_input)
        else:
            parsed_dict = self.parsed_input
        json_payload = json.dumps(parsed_dict)
        encoded_json = urllib.parse.quote(json_payload)
        return self.get(f'project/{self.project_id}/digest_delivery?json={encoded_json}')

    def jsonify_input(self, parsed_args):
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
        delivery = self.delivery
        if not self.output_file:
            if isinstance(delivery, str):
                soup = bs4.BeautifulSoup(delivery, features="html5lib")
                return sys.stdout.write(soup.get_text())
            return sys.stdout.write(json.dumps(delivery["DB_ACTION_OUTPUT"][0]))
        if not delivery:
            raise EmptyGetError
        with open(self.output_file, "w", encoding="utf-8") as out_pair_file:
            json.dump(delivery["DB_ACTION_OUTPUT"][0], out_pair_file, ensure_ascii=False, indent=4)
            logger.info(f"Delivery file written to {self.output_file}")

    def func(self, parsed_args):
        super().func(parsed_args)
        self.parsed_input = self.data()
        if not self.parsed_input:
            if parsed_args.specimen_name or parsed_args.sample_name or parsed_args.readset_name or parsed_args.specimen_id or parsed_args.sample_id or parsed_args.readset_id:
                self.parsed_input = self.jsonify_input(parsed_args)
            else:
                raise BadArgumentError("Use at least one of the following --specimen_<name|id>/--sample_<name|id>/--readset_<name|id> argument.")

        self.output_file = parsed_args.output
        self.json_to_delivery()
