import argparse
import json
import sys
import urllib.parse

from pt_cli.tools import AddCMD, BadArgumentError


class SampleGroup:
    """
    SampleGroup is a subparser of the client in which all sample group sub-commands are added.
    """

    __tool_name__ = 'sample_group'

    def __init__(self, subparser=argparse.ArgumentParser().add_subparsers()):
        self.subparser = subparser.add_parser(self.__tool_name__, help=self.help(), add_help=True).add_subparsers()

    def help(self):
        return (
            f"All {self.__tool_name__} sub commands, to list and edit the groups of samples analysed together. "
            f"Use 'pt_cli {self.__tool_name__} --help' to see more details."
        )


class List(AddCMD):
    """
    List is a sub-command of SampleGroup subparser using base AddCMD class
    """
    __tool_name__ = 'list'

    def help(self):
        return "List the sample groups of the project with their specimen and sample names"

    def arguments(self):
        self.parser.add_argument('--specimen_name', help='Only the groups of these specimens', nargs='+')
        self.parser.add_argument('--sample_group_name', help='Only these groups', nargs='+')

    def func(self, parsed_args):
        super().func(parsed_args)
        query = {}
        if parsed_args.specimen_name:
            query["specimen_name"] = list(parsed_args.specimen_name)
        if parsed_args.sample_group_name:
            query["sample_group_name"] = list(parsed_args.sample_group_name)
        path = f'project/{self.project_id}/sample_groups'
        if query:
            path += f'?json={urllib.parse.quote(json.dumps(query))}'
        response = self.get(path)
        sys.stdout.write(json.dumps(response.get("DB_ACTION_OUTPUT", []), indent=4))


class Edit(AddCMD):
    """
    Edit is a sub-command of SampleGroup subparser using base AddCMD class
    """
    __tool_name__ = 'edit'

    def help(self):
        return (
            "Add samples to a group (creating it when it doesn't exist) and/or remove samples. A group left without "
            "samples is deleted. Rename, deprecate or delete a group with 'pt-cli edit', 'deprecate' or 'delete' "
            "on the 'sample_group' table."
        )

    def arguments(self):
        self.parser.add_argument('--name', required=True, help='Sample group name')
        self.parser.add_argument('--add', help='Sample names to add', nargs='+')
        self.parser.add_argument('--remove', help='Sample names to remove', nargs='+')

    def func(self, parsed_args):
        super().func(parsed_args)
        if not (parsed_args.add or parsed_args.remove):
            raise BadArgumentError("Give --add and/or --remove.")
        payload = {"sample_group_name": parsed_args.name}
        if parsed_args.add:
            payload["add"] = list(parsed_args.add)
        if parsed_args.remove:
            payload["remove"] = list(parsed_args.remove)
        response = self.post(f'project/{self.project_id}/sample_group', data=json.dumps(payload))
        sys.stdout.write(json.dumps(response.get("DB_ACTION_OUTPUT", []), indent=4))


def register_sample_group_commands(subparser, connection_obj):
    sample_group_subparser = SampleGroup(subparser).subparser
    List(connection_obj=connection_obj, subparser=sample_group_subparser)
    Edit(connection_obj=connection_obj, subparser=sample_group_subparser)
