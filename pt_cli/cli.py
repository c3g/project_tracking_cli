#!/usr/bin/env python3
import json
import os
import pathlib
import sys
import logging
import urllib.parse

import shtab
import yaml

from pt_cli.connect import NotLoggedInError, Pt_Cli
from pt_cli.admin import register_admin_commands
from pt_cli.digest import register_digest_commands
from pt_cli.ingest import register_ingest_commands
from pt_cli.modification import register_modification_commands
from pt_cli.sample_group import register_sample_group_commands

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
    group.add_argument('--data-file', help='File use in a post', type=argparse.FileType('r'), default=None).complete = shtab.FILE # type: ignore
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
        # Default: ~/.config/pt_cli/tokens/<API host>.json, one token per API
        "token_file": None,
        "project": None,
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
        if not config['token_file']:
            config['token_file'] = f"~/.config/pt_cli/tokens/{url_root.netloc or 'default'}.json"
        sys.stdout.write('Config:\n')
        for key, value in config.items():
            if key == 'password' and value:
                value = '********'
            sys.stdout.write(f'{key}: {value}\n')
        sys.exit(0)

    session_file = pathlib.Path(config['session_file']).expanduser()
    token_file = pathlib.Path(
        config['token_file'] or f"~/.config/pt_cli/tokens/{url_root.netloc or 'default'}.json"
    ).expanduser()
    connector_session = Pt_Cli(config['project'], config['user'], config['password'], parsed.quiet, url_root.geturl(),
                               session_file=session_file, token_file=token_file)


    subparser = parser.add_subparsers(help='use the api routes directly')

    def help(parsed_local):
        help_content = connector_session.help()
        if isinstance(help_content, str):
            return sys.stdout.write(help_content)
        else:
            return sys.stdout.write(json.dumps(help_content))

    help_parser = subparser.add_parser(
        'help',
        help='List all available url/routes in the project tracking api. All these routes can be reached with the "url <url>" sub-command all other subcommand are convenience wrapper around these routes.',
        add_help=False
        )
    help_parser.set_defaults(func=help)

    def route(parsed_local):
        # Only clean the path: the query string may hold URIs such as "abacus:///path"
        path, sep, query = parsed_local.url.partition('?')
        while '//' in path:
            path = path.replace('//', '/')
        url = path.strip('/') + sep + query
        method = parsed_local.method if parsed_local.method else ('POST' if post_data else 'GET')

        if method == 'POST':
            logger.debug(f'POST to {url}')
            response = connector_session.post(url, post_data or '')
        else:
            logger.debug(f'GET from {url}')
            response = connector_session.get(url)

        if isinstance(response, list) and response:
            return sys.stdout.write('\n'.join([json.dumps(item) for item in response]))

        if not isinstance(response, str) and response:
            return sys.stdout.write(json.dumps(response))

    parser_url = subparser.add_parser('route', help='To use any url described in help', add_help=False)
    parser_url.add_argument('url')
    parser_url.add_argument('--method', choices=['GET', 'POST'], default=None,
                            help='Explicit HTTP method. If omitted, POST is used when --data/--data-file is provided, otherwise GET.')
    parser_url.set_defaults(func=route)

    def projects(parsed_local):
        return sys.stdout.write(json.dumps(connector_session.projects()))

    parser_project = subparser.add_parser('projects', help='List all projects', add_help=False)
    parser_project.set_defaults(func=projects)

    def vocabulary(parsed_local):
        return sys.stdout.write(json.dumps(connector_session.vocabulary(), indent=4))

    parser_vocabulary = subparser.add_parser(
        'vocabulary',
        help='List the controlled vocabularies: enum values and the analysis operations accepted by ingest analysis',
        add_help=False
    )
    parser_vocabulary.set_defaults(func=vocabulary)

    def login(parsed_local):
        connector_session.token.login()
        return sys.stderr.write(f"Logged in to {connector_session.root}: token kept in {token_file}\n")

    subparser.add_parser(
        'login',
        help="Log in to an API that checks tokens (COmanage): open the URL shown and enter the code. "
             "Other commands log in by themselves in a terminal; scripts without one need this first.",
        add_help=False
    ).set_defaults(func=login)

    def logout(parsed_local):
        if connector_session.token.logout():
            return sys.stderr.write(f"Logged out of {connector_session.root}: {token_file} deleted\n")
        return sys.stderr.write(f"Not logged in to {connector_session.root}\n")

    subparser.add_parser('logout', help='Forget the token of this API', add_help=False).set_defaults(func=logout)

    def token(parsed_local):
        access_token = connector_session.token.access_token(login=True)
        if not access_token:
            raise NotLoggedInError("Not logged in: run 'pt-cli login' in a terminal first.")
        return sys.stdout.write(access_token)

    subparser.add_parser(
        'token',
        help="Print the access token of this API, refreshed when needed, e.g. for Authorize in the API's /docs",
        add_help=False
    ).set_defaults(func=token)

    register_admin_commands(subparser=subparser, connection_obj=connector_session)
    register_digest_commands(subparser=subparser, connection_obj=connector_session)
    register_ingest_commands(subparser=subparser, connection_obj=connector_session)

    register_modification_commands(subparser=subparser, connection_obj=connector_session)
    register_sample_group_commands(subparser=subparser, connection_obj=connector_session)

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
