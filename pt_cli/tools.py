"""Module providing a sub commands to the client ot interact with the server"""

import argparse
import json
import logging
import sys

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
        sys.exit(str(self))

class EmptyGetError(Error):
    """docstring for EmptyGetError"""
    def __init__(self, message=None):
        super().__init__(message)
        if message:
            self.message = message
        else:
            self.message = "Database returned nothing, it's most likely unreachable"
        self.args = (f"{type(self).__name__}: {self.message}",)
        sys.exit(str(self))

class JSONDecodeError(Error):
    """Raised when JSON decoding fails."""
    def __init__(self, context, original_exception):
        message = f"Failed to decode JSON {context}: {original_exception}\n                 This is most likely not a JSON file or it's malformed."
        super().__init__(message)
        self.args = (f"{type(self).__name__}: {self.message}",)
        sys.exit(str(self))


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
        self._project_id = None
        self.parsed_args = None

    @property
    def project_id(self):
        """
        The project of the request: --project, the 'project' of connect.yaml or, for ingestion, the
        project_name of the payload (see project_from_payload)
        """
        project = self._project_id or self.connection_obj.project_id
        if not project:
            raise BadArgumentError("No project given: use --project or set 'project' in connect.yaml")
        return project

    def project_from_payload(self, payload):
        """
        Use the payload's project_name when no project is given; warn when the given project differs from it.
        """
        project_name = payload.get("project_name") if isinstance(payload, dict) else None
        if not project_name:
            return
        if not self.connection_obj.project_id:
            self._project_id = project_name
        elif str(self.connection_obj.project_id).lower() != str(project_name).lower():
            logging.warning(
                f"Ingesting into project '{self.connection_obj.project_id}' (--project or connect.yaml) "
                f"although the payload's project_name is '{project_name}'"
            )

    def data(self, error_if_missing=False):
        """
        :param error_if_missing: Will raise Error when true and no
        data is provided
        :return: The data to be posted to the server. This will be a
        string coming from a user provided file or directly from the
        command line

        """
        parsed_args = self.parsed_args
        if self._POSTED_DATA is None:
            if parsed_args is not None and getattr(parsed_args, 'data', None):
                self._POSTED_DATA = getattr(parsed_args, 'data')
            elif parsed_args is not None and getattr(parsed_args, 'data_file', None):
                data_file = getattr(parsed_args, 'data_file')
                self._POSTED_DATA = data_file.read()
                data_file.close()
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
