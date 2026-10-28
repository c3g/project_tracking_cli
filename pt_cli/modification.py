from pt_cli.tools import AddCMD, BadArgumentError, safe_json_loads

import argparse
import json
import sys

import shtab


def _write_db_action_output(response):
    if not isinstance(response, dict):
        return
    output = response.get("DB_ACTION_OUTPUT", [])
    if isinstance(output, list):
        sys.stdout.write("\n".join([str(item) for item in output]))


def register_modification_commands(subparser, connection_obj):
    Edit(connection_obj=connection_obj, subparser=subparser)
    Delete(connection_obj=connection_obj, subparser=subparser)
    UnDelete(connection_obj=connection_obj, subparser=subparser)
    Deprecate(connection_obj=connection_obj, subparser=subparser)
    UnDeprecate(connection_obj=connection_obj, subparser=subparser)
    Curate(connection_obj=connection_obj, subparser=subparser)


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
        self.parser.add_argument('--input-json', help="Json file containing all information to be edited on the database", type=argparse.FileType('r')).complete = shtab.FILE  # type: ignore[attr-defined]
        self.parser.add_argument('--dry_run', action='store_true', default=False, help="If set, will only print the entries that will be curated without actually curating them.")

    @property
    def edit(self):
        return self.post(f'project/{self.project_id}/modification/edit', data=self.edit_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        self.edit_input = self.data()
        if not self.edit_input and parsed_args.input_json:
            self.edit_input = parsed_args.input_json.read()
            parsed_args.input_json.close()
        if not self.edit_input:
            raise BadArgumentError

        if parsed_args.dry_run:
            self.edit_input = safe_json_loads(self.edit_input)
            self.edit_input["dry_run"] = True
            self.edit_input = json.dumps(self.edit_input, ensure_ascii=False, indent=4)

        response = self.edit
        if isinstance(response, str) and response.startswith("Welcome"):
            pass
        else:
            _write_db_action_output(response)


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
        self.parser.add_argument('--input-json', help="Json file containing all information to be deleted on the database", type=argparse.FileType('r')).complete = shtab.FILE  # type: ignore[attr-defined]
        self.parser.add_argument('--dry_run', action='store_true', default=False, help="If set, will only print the entries that will be curated without actually curating them.")
        self.parser.add_argument('--cascade_down', help="Also delete the rows below them whose parents are then all deleted: samples, readsets, files, locations, metrics, jobs, sample groups", action='store_true', default=False)
        self.parser.add_argument('--cascade_up', help="Also delete a sample, specimen or file once all its readsets, samples or locations are deleted", action='store_true', default=False)
        self.parser.add_argument('--cascade', help="Both --cascade_down and --cascade_up", action='store_true', default=False)

    @property
    def delete(self):
        return self.post(f'project/{self.project_id}/modification/delete', data=self.delete_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        self.delete_input = self.data()
        if not self.delete_input and parsed_args.input_json:
            self.delete_input = parsed_args.input_json.read()
            parsed_args.input_json.close()
        if not self.delete_input:
            raise BadArgumentError

        if parsed_args.dry_run:
            self.delete_input = safe_json_loads(self.delete_input)
            self.delete_input["dry_run"] = True
            self.delete_input = json.dumps(self.delete_input, ensure_ascii=False, indent=4)

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
            _write_db_action_output(response)


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
        self.parser.add_argument('--input-json', help="Json file containing all information to be undeleted on the database", type=argparse.FileType('r')).complete = shtab.FILE  # type: ignore[attr-defined]
        self.parser.add_argument('--dry_run', action='store_true', default=False, help="If set, will only print the entries that will be curated without actually curating them.")
        self.parser.add_argument('--cascade_down', help="Also undelete the deleted rows below them", action='store_true', default=False)
        self.parser.add_argument('--cascade_up', help="Also undelete their deleted sample, specimen or file (not their siblings)", action='store_true', default=False)
        self.parser.add_argument('--cascade', help="Both --cascade_down and --cascade_up", action='store_true', default=False)

    @property
    def undelete(self):
        return self.post(f'project/{self.project_id}/modification/undelete', data=self.undelete_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        self.undelete_input = self.data()
        if not self.undelete_input and parsed_args.input_json:
            self.undelete_input = parsed_args.input_json.read()
            parsed_args.input_json.close()
        if not self.undelete_input:
            raise BadArgumentError

        if parsed_args.dry_run:
            self.undelete_input = safe_json_loads(self.undelete_input)
            self.undelete_input["dry_run"] = True
            self.undelete_input = json.dumps(self.undelete_input, ensure_ascii=False, indent=4)

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
            _write_db_action_output(response)


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
        self.parser.add_argument('--input-json', help="Json file containing all information to be deprecated on the database", type=argparse.FileType('r')).complete = shtab.FILE  # type: ignore[attr-defined]
        self.parser.add_argument('--dry_run', action='store_true', default=False, help="If set, will only print the entries that will be curated without actually curating them.")
        self.parser.add_argument('--cascade_down', help="Also deprecate the rows below them whose parents are then all deprecated: samples, readsets, files, locations, metrics, jobs, sample groups", action='store_true', default=False)
        self.parser.add_argument('--cascade_up', help="Also deprecate a sample, specimen or file once all its readsets, samples or locations are deprecated", action='store_true', default=False)
        self.parser.add_argument('--cascade', help="Both --cascade_down and --cascade_up", action='store_true', default=False)

    @property
    def deprecate(self):
        return self.post(f'project/{self.project_id}/modification/deprecate', data=self.deprecate_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        self.deprecate_input = self.data()
        if not self.deprecate_input and parsed_args.input_json:
            self.deprecate_input = parsed_args.input_json.read()
            parsed_args.input_json.close()
        if not self.deprecate_input:
            raise BadArgumentError

        if parsed_args.dry_run:
            self.deprecate_input = safe_json_loads(self.deprecate_input)
            self.deprecate_input["dry_run"] = True
            self.deprecate_input = json.dumps(self.deprecate_input, ensure_ascii=False, indent=4)

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
            _write_db_action_output(response)


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
        self.parser.add_argument('--input-json', help="Json file containing all information to be undeprecated on the database", type=argparse.FileType('r')).complete = shtab.FILE  # type: ignore[attr-defined]
        self.parser.add_argument('--dry_run', action='store_true', default=False, help="If set, will only print the entries that will be curated without actually curating them.")
        self.parser.add_argument('--cascade_down', help="Also undeprecate the deprecated rows below them", action='store_true', default=False)
        self.parser.add_argument('--cascade_up', help="Also undeprecate their deprecated sample, specimen or file (not their siblings)", action='store_true', default=False)
        self.parser.add_argument('--cascade', help="Both --cascade_down and --cascade_up", action='store_true', default=False)

    @property
    def undeprecate(self):
        return self.post(f'project/{self.project_id}/modification/undeprecate', data=self.undeprecate_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        self.undeprecate_input = self.data()
        if not self.undeprecate_input and parsed_args.input_json:
            self.undeprecate_input = parsed_args.input_json.read()
            parsed_args.input_json.close()
        if not self.undeprecate_input:
            raise BadArgumentError

        if parsed_args.dry_run:
            self.undeprecate_input = safe_json_loads(self.undeprecate_input)
            self.undeprecate_input["dry_run"] = True
            self.undeprecate_input = json.dumps(self.undeprecate_input, ensure_ascii=False, indent=4)

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
            _write_db_action_output(response)


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
        self.parser.add_argument('--input-json', help="Json file containing all information to be curated from the database", type=argparse.FileType('r')).complete = shtab.FILE  # type: ignore[attr-defined]
        self.parser.add_argument('--dry_run', action='store_true', default=False, help="If set, will only print the entries that will be curated without actually curating them.")
        self.parser.add_argument('--cascade_down', help="Also curate the rows below them whose parents are then all curated: samples, readsets, files, locations, metrics, jobs, sample groups. Curate refuses to remove rows the request doesn't reach", action='store_true', default=False)
        self.parser.add_argument('--cascade_up', help="Also curate a sample, specimen or file once all its readsets, samples or locations are curated", action='store_true', default=False)
        self.parser.add_argument('--cascade', help="Both --cascade_down and --cascade_up", action='store_true', default=False)

    @property
    def curate(self):
        return self.post(f'project/{self.project_id}/modification/curate', data=self.curate_input)

    def func(self, parsed_args):
        super().func(parsed_args)
        self.curate_input = self.data()
        if not self.curate_input and parsed_args.input_json:
            self.curate_input = parsed_args.input_json.read()
            parsed_args.input_json.close()

        if not self.curate_input:
            raise BadArgumentError

        if parsed_args.dry_run:
            self.curate_input = safe_json_loads(self.curate_input)
            self.curate_input["dry_run"] = True
            self.curate_input = json.dumps(self.curate_input, ensure_ascii=False, indent=4)

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
            _write_db_action_output(response)
