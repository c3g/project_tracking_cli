#!/usr/bin/env python3.11
import errno
import json
import os
import pathlib
import sys
import logging
import urllib.parse

import bs4
import yaml

try:
    from pt_cli.connect import Pt_Cli
    from pt_cli.tools import ReadsetFile
except ModuleNotFoundError:
    from connect import Pt_Cli
    from tools import ReadsetFile

logger = logging.getLogger(__name__)


def main(args=None, set_logger=True):

    if args is None:
        args = sys.argv[1:]

    import argparse


    parser = argparse.ArgumentParser()

    parser.add_argument('--url_root', help='Where the server is located, will overwrite '
                                           'value in the ~/.config/pt_cli/connect.yaml config file.'
                                           'Should be of the "http(s)://location" form')
    parser.add_argument('--project', help='project you are working on', default='MOH-Q')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--data-file', help='file use in a post', type=argparse.FileType('r'), default=None)
    group.add_argument('--data', help='string to use in a post', default=None)
    parser.add_argument('--loglevel', help='set log level', choices=logging._levelToName.values(), default='INFO')

    # The cli help is handled later once all option and command are stored
    parsed = parser.parse_known_args(args=[a for a in args if a not in ['-h', '--help']])[0]


    post_data = None
    if parsed.data is not None:
        post_data = parser.data
    elif parsed.data_file is not None:
        post_data = parsed.data_file.read()
        parsed.data_file.close()

    url_root = parsed.url_root
    project = parsed.project

    if set_logger:
        # logs all go to stderr so only the payload from the server is sent to stdout.
        logging.basicConfig(format='%(levelname)s:%(message)s', level=parsed.loglevel, stream=sys.stderr)

    config_files = ['~/.config/pt_cli/connect.yaml', './connect.yaml']
    config = {'session_file': '~/.pt_cli'}
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

    if project:
        config['project'] = project
    if url_root:
        config['url_root'] = url_root
    url_root = urllib.parse.urlparse(config['url_root'])

    if not url_root.scheme:
        url_root._replace(scheme='http')

    session_file = pathlib.Path(config['session_file']).expanduser()
    connector_session = Pt_Cli(config['project'], url_root.geturl(), session_file=session_file)

    subparser = parser.add_subparsers(help='use the api routes directly')

    def help(parsed_local):
        return sys.stdout.write(connector_session.help())
    help_parser = subparser.add_parser('help', help='List all available url/routes in the project tracking api.'
                                                     'All these routes can be reached with the "url <url>" sub-command'
                                                     'all other subcommand are convenience wrapper around these routes.')
    help_parser.set_defaults(func=help)

    def route(parsed_local):
        if post_data:
            response = connector_session.post(parsed_local.url, post_data)
        else:
            response = connector_session.get(parsed_local.url)

        if isinstance(response, str):
            soup = bs4.BeautifulSoup(response, features="lxml")
            return sys.stdout.write(soup.get_text())
        else:
            return sys.stdout.write(json.dumps(response))

    parser_url = subparser.add_parser('route', help='To use any url described in help')
    parser_url.add_argument('url')
    parser_url.set_defaults(func=route)

    def projects(parsed_local):
        return sys.stdout.write(json.dumps(connector_session.projects()))

    parser_project = subparser.add_parser('projects', help='list all projects')
    parser_project.set_defaults(func=projects)



    ReadsetFile(connection_obj=connector_session, subparser=subparser)


    subparsed = parser.parse_args(args=args)


    # Calling the api:
    subparsed.func(subparsed)
    # make sure pipes are not broken
    sys.stdout.write('\n')
    sys.stdout.flush()




if __name__ == '__main__':

    main()
