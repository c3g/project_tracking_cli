#!/usr/bin/env python3
import json
import os
import pathlib
import sys
import logging
import urllib.parse

import shtab
import yaml

from pt_cli.connect import Pt_Cli
from pt_cli.tools import (
        Digest,
        Ingest,
        ReadsetFile,
        PairFile,
        Unanalyzed,
        Delivery,
        RunProcessing,
        Transfer,
        GenPipes,
        Edit,
        Delete,
        UnDelete,
        Deprecate,
        UnDeprecate,
        Curate,
        GetID,
        Location,
        )

from .__version__ import __version__

logger = logging.getLogger(__name__)


def get_main_parser(args=None):
    if args is None:
        args = sys.argv[1:]

    import argparse


    parser = argparse.ArgumentParser()

    parser.add_argument('--url-root', help='Where the server is located, will overwrite value in the ~/.config/pt_cli/connect.yaml config file. Should be of the "http(s)://location" form', default=None)
    parser.add_argument('--project', help='Project you are working on', default=None)

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--data-file', help='File use in a post', type=argparse.FileType('r'), default=None).complete = shtab.FILE
    group.add_argument('--data', help='String to use in a post', default=None)
    parser.add_argument('--loglevel', help='Set log level', choices=list(logging._levelToName.values()), default='INFO')
    parser.add_argument('--info', help='Get current client config', action='store_true')
    parser.add_argument('-q', '--quiet', help='Writes Warnings to a file instead of stdout', action='store_true')
    parser.add_argument('-v', '--version', help='Show version', action="version", version=f'{__version__}')

    return parser

def main(args=None, set_logger=True):

    if args is None:
        args = sys.argv[1:]

    parser = get_main_parser()
    # The cli help is handled later once all option and command are stored
    parsed = parser.parse_known_args(args=[a for a in args if a not in ['-h', '--help']])[0]


    post_data = None
    if parsed.data is not None:
        post_data = parsed.data
    elif parsed.data_file is not None:
        post_data = parsed.data_file.read()
        parsed.data_file.close()

    if set_logger:
        # logs all go to stderr so only the payload from the server is sent to stdout.
        logging.basicConfig(format='%(levelname)s:%(message)s', level=parsed.loglevel, stream=sys.stderr)

    # Cli Configuration setup
    # Default
    config = {
        "url_root": "https://c3g-portal.sd4h.ca",
        "session_file": "~/.pt_cli",
        "project": "moh-q",
        "user": None,
        "password": None
        }

    # Config file overwrite
    config_files = ['~/.config/pt_cli/connect.yaml', './connect.yaml']
    i = 0
    while i < len(config_files):
        file = os.path.expanduser(config_files[i])
        if os.path.isfile(file):
            with open(file) as fp:
                config.update(yaml.load(fp, Loader=yaml.SafeLoader))
                extra_config = config.get('config_file', None)
                if extra_config:
                    config_files.insert(i, extra_config)
        i += 1
    # Command line overwrite
    if parsed.project:
        config['project'] = parsed.project
    if parsed.url_root:
        config['url_root'] = parsed.url_root
    url_root = urllib.parse.urlparse(config['url_root'])

    if not url_root.scheme:
        url_root._replace(scheme='http')

    if parsed.info:
        sys.stdout.write('Config:\n')
        for key, value in config.items():
            sys.stdout.write(f'{key}: {value}\n')
        sys.exit(0)

    session_file = pathlib.Path(config['session_file']).expanduser()
    connector_session = Pt_Cli(config['project'], config['user'], config['password'], parsed.quiet, url_root.geturl(), session_file=session_file)


    subparser = parser.add_subparsers(help='use the api routes directly')

    def help(parsed_local):
        return sys.stdout.write(connector_session.help())

    help_parser = subparser.add_parser(
        'help',
        help='List all available url/routes in the project tracking api. All these routes can be reached with the "url <url>" sub-command all other subcommand are convenience wrapper around these routes.',
        add_help=False
        )
    help_parser.set_defaults(func=help)

    def route(parsed_local):
        url = parsed_local.url.replace('//', '/').strip('/')
        if post_data:
            logger.debug(f'POST to {url}')
            response = connector_session.post(url, post_data)
        else:
            logger.debug(f'GET from {url}')
            response = connector_session.get(url)

        if not isinstance(response, str):
            return sys.stdout.write(json.dumps(response))

    parser_url = subparser.add_parser('route', help='To use any url described in help', add_help=False)
    parser_url.add_argument('url')
    parser_url.set_defaults(func=route)

    def projects(parsed_local):
        return sys.stdout.write(json.dumps(connector_session.projects()))

    parser_project = subparser.add_parser('projects', help='List all projects', add_help=False)
    parser_project.set_defaults(func=projects)

    digest_subparser = Digest(subparser).subparser
    ReadsetFile(connection_obj=connector_session, subparser=digest_subparser)
    PairFile(connection_obj=connector_session, subparser=digest_subparser)
    Unanalyzed(connection_obj=connector_session, subparser=digest_subparser)
    Delivery(connection_obj=connector_session, subparser=digest_subparser)

    ingest_subparser = Ingest(subparser).subparser
    RunProcessing(connection_obj=connector_session, subparser=ingest_subparser)
    Transfer(connection_obj=connector_session, subparser=ingest_subparser)
    GenPipes(connection_obj=connector_session, subparser=ingest_subparser)

    Edit(connection_obj=connector_session, subparser=subparser)
    Delete(connection_obj=connector_session, subparser=subparser)
    UnDelete(connection_obj=connector_session, subparser=subparser)
    Deprecate(connection_obj=connector_session, subparser=subparser)
    UnDeprecate(connection_obj=connector_session, subparser=subparser)
    Curate(connection_obj=connector_session, subparser=subparser)

    getid_subparser = GetID(subparser).subparser
    Location(connection_obj=connector_session, subparser=getid_subparser)

    shtab.add_argument_to(parser, ["-s", "--print-completion"])


    subparsed = parser.parse_args(args=args)

    # a subcommand needs to be provided
    # for func to exist
    if getattr(subparsed, 'func', None):
        subparsed.func(subparsed)
        sys.stdout.write('\n')
        sys.stdout.flush()
    else:
        parser.print_help()


if __name__ == '__main__':

    main()
