import argparse
import json
import sys

from pt_cli.tools import AddCMD


def _write_json_response(response):
    if isinstance(response, list) and response:
        sys.stdout.write('\n'.join([json.dumps(item) for item in response]))
        return

    if not isinstance(response, str) and response:
        sys.stdout.write(json.dumps(response))


class Admin:
    """
    Admin is a subparser of the client in which all admin sub-commands are added.
    """

    __tool_name__ = 'admin'

    def __init__(self, subparser=argparse.ArgumentParser().add_subparsers()):
        self.subparser = subparser.add_parser(self.__tool_name__, help=self.help(), add_help=True).add_subparsers()

    def help(self):
        return (
            f"All {self.__tool_name__} sub commands, those encapsulate admin-restricted operations. "
            f"Use 'pt_cli {self.__tool_name__} --help' to see more details."
        )


class CreateProject(AddCMD):
    """
    CreateProject is a sub-command of Admin subparser using base AddCMD class.
    """

    __tool_name__ = 'create-project'

    def help(self):
        return 'Create or fetch a project by name via /admin/create_project/<project_name>'

    def arguments(self):
        self.parser.add_argument('--name', required=True, help='Project name used in route path')
        self.parser.add_argument('--database', default=None,
                                 help='Label of the database the project goes in (e.g. project_tracking_cphi): required '
                                      'when the API has several databases; everyone who reads it reads the project')
        self.parser.add_argument('--ext-id', type=int, default=None, help='Optional external identifier')
        self.parser.add_argument('--ext-src', default=None, help='Optional external source label for ext-id')

    def func(self, parsed_args):
        super().func(parsed_args)

        payload = {}
        if parsed_args.database is not None:
            payload['database'] = parsed_args.database
        if parsed_args.ext_id is not None:
            payload['ext_id'] = parsed_args.ext_id
        if parsed_args.ext_src is not None:
            payload['ext_src'] = parsed_args.ext_src

        response = self.post(
            f'admin/create_project/{parsed_args.name}',
            data=json.dumps(payload) if payload else ''
        )
        _write_json_response(response)


class Databases(AddCMD):
    """
    Databases is a sub-command of Admin subparser using base AddCMD class.
    """

    __tool_name__ = 'databases'

    def help(self):
        return 'List the databases (the labels create-project --database takes) and their projects via /admin/databases'

    def arguments(self):
        self.parser.add_argument('--json', action='store_true', help='Print the JSON response instead of a table')

    def func(self, parsed_args):
        super().func(parsed_args)

        response = self.get('admin/databases')
        if parsed_args.json:
            _write_json_response(response)
            return
        rows = response.get('DB_ACTION_OUTPUT', []) if isinstance(response, dict) else []
        width = max((len(row['database']) for row in rows), default=0)
        for row in rows:
            projects = row.get('error') or ', '.join(row['projects']) or '(no project)'
            sys.stdout.write(f"{row['database']:<{width}}  {projects}\n")


def register_admin_commands(subparser, connection_obj):
    admin_subparser = Admin(subparser).subparser
    CreateProject(connection_obj=connection_obj, subparser=admin_subparser)
    Databases(connection_obj=connection_obj, subparser=admin_subparser)
