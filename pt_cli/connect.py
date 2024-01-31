import sys
import inspect

import getpass
import json
import pickle
import re
import weakref
import logging

import requests
import bs4

logger = logging.getLogger(__name__)


class Error(Exception):
    """docstring for Error"""
    def __init__(self, msg):
        if isinstance(msg, list):
            self.args = (f"{type(self).__name__}: \n{chr(10).join(msg)}",)
        else:
            self.args = (f"{type(self).__name__}: {msg}",)
        sys.exit(self)

class BadRequestError(Error):
    """docstring for BadRequestError"""

class OAuthNego():
    """
    The base class to create python client that is able to
    get the oauth-proxy token/cookie
    """


    CSRF = "_oauth2_proxy_csrf"
    REDIRECT = 'redirect_uri'
    AUTH_SESSION_ID = 'AUTH_SESSION_ID'
    AUTH_SESSION_ID_LEGACY = 'AUTH_SESSION_ID_LEGACY'
    KC_RESTART = 'KC_RESTART'
    PARAMS = ['session_code', 'execution', 'client_id', 'tab_id']

    def __init__(self, root, session_file):
        self.root = root
        self.cookies = {}
        self.user = None
        self.password = None
        # Initialise session from file
        self.session_file = session_file
        if session_file.is_file():
            self.s = self.load_session(session_file)
        else:
            self.s = requests.session()
        # save session at the end
        self._finalizer = \
            weakref.finalize(self, self.save_session, self.session_file, self.s)
        data_type = None

    @classmethod
    def save_session(cls, file, session):
        with open(file, 'wb') as fp:
            pickle.dump(session, fp)

    @classmethod
    def load_session(cls, file):
        with open(file, 'rb') as fp:
            s = pickle.load(fp)
        return s

    def prompt_pw(self):
        if self.user:
            user = self.user
        else:
            user = input("Username:")
        if self.password:
            password = self.password
        else:
            password = getpass.getpass()
        return {'username': user, 'password': password, 'credentialId': ''}

    def connect(self, r_get):
        """
        This is pretty specific to keycloak,
        need to find something more specific for when we will
        use CAF or cilogon
        :return:
        """
        params = {}
        decoded_content = r_get.content.decode()
        for k in self.PARAMS:
            params[k] = re.search(f'{k}=(.*?)&', decoded_content).groups()[0]
        post_url = re.search(r'(https://.*?)\?', decoded_content).groups()[0]
        return self.s.post(post_url, params=params, data=self.prompt_pw())

    def maybe_json(self, data):
        try:
            loads = json.loads(data)
            if isinstance(loads, dict):
                if loads.get("DB_ACTION_ERROR"):
                    raise BadRequestError(loads.get("DB_ACTION_ERROR"))
                if loads.get("DB_ACTION_WARNING"):
                    raise BadRequestError(loads.get("DB_ACTION_WARNING"))
            self.data_type = 'json'
            return loads
        except json.decoder.JSONDecodeError:
            if isinstance(data, str):
                soup = bs4.BeautifulSoup(data, features="lxml")
                if soup.get_text().startswith("----------"):
                    sys.stdout.write(soup.get_text())
                elif soup.get_text().startswith("Welcome"):
                    sys.stdout.write(soup.get_text())
                else:
                    raise BadRequestError(soup.get_text())
            return data

    def get(self, path):
        url = f"{self.root}/{path}"
        r_get = self.s.get(url)
        # If the api is protected and the session does
        # not have the required token or cookie
        # we get a redirect
        if self.REDIRECT in r_get.url:
            self.connect(r_get)
            r_get = self.s.get(url)

        return self.maybe_json(r_get.text)

    def post(self, path, data):
        url = f"{self.root}/{path}"
        r_post = self.s.post(url, data=data)
        # If the api is protected and the session does
        # not have the required token or cookie
        # we get a redirect
        if self.REDIRECT in r_post.url:
            r_post = self.connect(r_post)

        return self.maybe_json(r_post.text)


class Pt_Cli(OAuthNego):
    """
    The cli always connect to a specific project, convenience method can be implemented here.
    """
    def __init__(self, project_id, user, password, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_id = project_id
        self.user = user
        self.password = password

    def projects(self):
        return self.get("project")

    def help(self):
        return self.get("help")
