import argparse
import json
import sys

import shtab

from pt_cli.tools import AddCMD, BadArgumentError, safe_json_loads


def _write_db_action_output(response):
    if not isinstance(response, dict):
        return
    output = response.get("DB_ACTION_OUTPUT", [])
    if isinstance(output, list) and output:
        sys.stdout.write("\n".join([json.dumps(item) for item in output]))


class Ingest:
    """
    Ingest is a subparser of the client in which all ingestion sub-commands are added.
    """

    __tool_name__ = 'ingest'

    def __init__(self, subparser=argparse.ArgumentParser().add_subparsers()):
        self.subparser = subparser.add_parser(self.__tool_name__, help=self.help(), add_help=True).add_subparsers()

    def help(self):
        return (
            f"All {self.__tool_name__} sub commands, those encapsulate all operation pushing "
            f"information into the database. Use 'pt_cli {self.__tool_name__} --help' to see more details."
        )


def register_ingest_commands(subparser, connection_obj):
    ingest_subparser = Ingest(subparser).subparser
    RunProcessing(connection_obj=connection_obj, subparser=ingest_subparser)
    Transfer(connection_obj=connection_obj, subparser=ingest_subparser)
    GenPipes(connection_obj=connection_obj, subparser=ingest_subparser)
    DeliveryIngest(connection_obj=connection_obj, subparser=ingest_subparser)


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
        self.parser.add_argument('--input-json', help="Json file containing all information to add data from Run Processing into the database", type=argparse.FileType('r')).complete = shtab.FILE  # type: ignore[attr-defined]

    @property
    def run_processing(self):
        return self.post(f'project/{self.project_id}/ingest_run_processing', data=self.run_processing_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        self.run_processing_input = self.data()
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
            _write_db_action_output(response)


class Transfer(AddCMD):
    """
    Transfer is a sub-command of Ingest subparser using base AddCMD class
    """
    __tool_name__ = 'transfer'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transfer_input = None

    def help(self):
        return "Will push a Transfer of data (copy, rsync, mv, etc) into the database"

    def arguments(self):
        self.parser.add_argument('--input-json', help="Json file containing all information to add data from a Transfer into the database", type=argparse.FileType('r')).complete = shtab.FILE  # type: ignore[attr-defined]

    @property
    def transfer(self):
        return self.post(f'project/{self.project_id}/ingest_transfer', data=self.transfer_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        self.transfer_input = self.data()
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
            _write_db_action_output(response)


class GenPipes(AddCMD):
    """
    GenPipes is a sub-command of Ingest subparser using base AddCMD class
    """
    __tool_name__ = 'genpipes'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.genpipes_input = None

    def help(self):
        return "Will push a GenPipes analysis into the database"

    def arguments(self):
        self.parser.add_argument('--input-json', help="Json file containing all information to add a GenPipes analysis into the database", type=argparse.FileType('r')).complete = shtab.FILE  # type: ignore[attr-defined]

    @property
    def genpipes(self):
        return self.post(f'project/{self.project_id}/ingest_genpipes', data=self.genpipes_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        self.genpipes_input = self.data()
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
            _write_db_action_output(response)


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
        self.parser.add_argument('--input-json', help="Json file containing all information to add data from a Delivery into the database", type=argparse.FileType('r')).complete = shtab.FILE  # type: ignore[attr-defined]
        self.parser.add_argument('--delete', action='store_true', default=True, help="By default, delivery will delete the files from their original location after transfer. If you want to keep the original files, set this flag to False.")

    @property
    def delivery(self):
        return self.post(f'project/{self.project_id}/ingest_delivery', data=self.delivery_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        self.delivery_input = self.data()
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
            _write_db_action_output(response)
