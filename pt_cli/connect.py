import sys
import inspect

import getpass
import json
import os
import pickle
import re
import weakref
import logging

import requests
import bs4

logger = logging.getLogger(__name__)


class Error(Exception):
    """An error that ends pt-cli: the message goes to stderr and the exit code is exit_code"""
    exit_code = 1

    def __init__(self, msg):
        if isinstance(msg, list):
            self.args = (f"{type(self).__name__}: \n{chr(10).join(msg)}",)
        else:
            self.args = (f"{type(self).__name__}: {msg}",)
        sys.stderr.write(f"{self.args[0]}\n")
        sys.exit(self.exit_code)

class BadRequestError(Error):
    """docstring for BadRequestError"""

class NotLoggedInError(Error):
    """The API needs a token and pt-cli has none that works: run 'pt-cli login'"""
    exit_code = 3

class NotAllowedError(Error):
    """The token is valid but its groups don't give the role the route needs"""
    exit_code = 4


class BearerToken():
    """
    The COmanage token of an API with AUTH_MODE 'oidc'. pt-cli logs in with a device code through the API's
    /auth/* routes, which add the API's client secret: pt-cli never holds a secret. The token is cached in
    token_file, one file per API.
    """
    # Any value: the API sends its own client id to COmanage
    CLIENT_ID = 'pt-cli'

    def __init__(self, root, token_file):
        self.root = root
        self.token_file = token_file
        self._session = None

    def session(self):
        if self._session is None:
            try:
                from c3g_oidc.client import DeviceCodeSession
            except ImportError:
                raise Error("This API needs a login, which needs the 'oidc' extra: pip install 'pt_cli[oidc]'")
            self._session = DeviceCodeSession(
                self.root,
                self.CLIENT_ID,
                str(self.token_file),
                display=lambda message: sys.stderr.write(f"{message}\n"),
                device_authorization_endpoint=f"{self.root}/auth/device_authorization",
                token_endpoint=f"{self.root}/auth/token",
            )
        return self._session

    @staticmethod
    def interactive():
        """Someone can open the login URL: stderr is a terminal (not a cron job)"""
        return sys.stdin.isatty() and sys.stderr.isatty()

    def login(self):
        """Log in with a device code; return the access token"""
        from c3g_oidc.client import DeviceLoginError
        session = self.session()
        try:
            return session.login()
        except (DeviceLoginError, requests.RequestException, ValueError, KeyError) as error:
            raise NotLoggedInError(f"Login failed: {error}")

    def access_token(self, login=False):
        """
        The cached token, refreshed when it expired, or None without one. With login, log in when there is no
        usable token and someone is at the terminal.
        """
        if not os.path.exists(self.token_file) and not login:
            return None
        from c3g_oidc.client import DeviceLoginError
        session = self.session()
        try:
            return session.get_access_token(interactive=False)
        except DeviceLoginError:
            if login and self.interactive():
                return self.login()
            return None

    def headers(self):
        token = self.access_token()
        return {'Authorization': f'Bearer {token}'} if token else {}

    def logout(self):
        """Forget the cached token; return whether there was one"""
        existed = os.path.exists(self.token_file)
        if existed:
            os.remove(self.token_file)
        return existed

class Warning(Exception):
    """docstring for Warning"""
    def __init__(self, msg):
        if isinstance(msg, list):
            self.args = (f"{type(self).__name__}: \n{chr(10).join(msg)}",)
        else:
            self.args = (f"{type(self).__name__}: {msg}",)

class BadRequestWarning(Warning):
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

    def __init__(self, root, session_file, token_file=None):
        self.root = root.strip('/')
        self.token = BearerToken(self.root, token_file)
        self.cookies = {}
        self.user = None
        self.password = None
        self.quiet = False
        # Initialise session from file
        self.session_file = session_file
        # if session_file.is_file():
        try:
            self.s = self.load_session(session_file)
        except (EOFError, FileNotFoundError) as e:
            self.s = requests.sessions.Session()

        data_type = None

    @classmethod
    def save_session(cls, file, session):
        with open(file, 'wb', buffering=0) as fp:
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

    def connect(self, r_get=None):
        """
        This is pretty specific to keycloak,
        need to find something less specific for when we will
        use CAF or cilogon
        :return:
        """
        # By default, connect on the welcome page
        if r_get is None:
            r_get = self.s.get(f"{self.root}/")

        params = {}
        decoded_content = r_get.content.decode()
        for k in self.PARAMS:
            params[k] = re.search(f'{k}=(.*?)&', decoded_content).groups()[0]
        post_url = re.search(r'(https://.*?)\?', decoded_content).groups()[0]
        connect = self.s.post(post_url, params=params, data=self.prompt_pw())
        self.save_session(self.session_file, self.s)
        return connect

    def maybe_json(self, data):
        try:
            loads = json.loads(data)
            if isinstance(loads, dict):
                if loads.get("DB_ACTION_ERROR"):
                    raise BadRequestError(loads.get("DB_ACTION_ERROR"))
                if loads.get("DB_ACTION_WARNING"):
                    db_action_warning = loads.get("DB_ACTION_WARNING")
                    if isinstance(db_action_warning, list):
                        db_action_warning = "\n".join(db_action_warning)
                    if self.quiet:
                        logger.warning("WARNINGS written to warning.log")
                        with open('warning.log', 'w') as f:
                            f.write(f"\n{db_action_warning}")
                    else:
                        logger.warning(f"\n{db_action_warning}")
                    loads.pop("DB_ACTION_WARNING")
            self.data_type = 'json'
            return loads
        except json.decoder.JSONDecodeError:
            if isinstance(data, str):
                soup = bs4.BeautifulSoup(data, features="html5lib")
                if soup.get_text().startswith("----------"):
                    # No more printing here otherwise it gets printed twice and without proper parsing
                    pass
                elif soup.get_text().startswith("Welcome"):
                    sys.stdout.write(soup.get_text())
                else:
                    raise BadRequestError(soup.get_text())
            return data

    @staticmethod
    def refusal(response):
        """The DB_ACTION_ERROR of a refused request, or its text"""
        try:
            error = response.json().get("DB_ACTION_ERROR")
            return "\n".join(error) if isinstance(error, list) else str(error)
        except (ValueError, AttributeError):
            return response.text

    def request(self, method, path, data=None):
        url = f"{self.root}/{path}"
        response = self.s.request(method, url, data=data, headers=self.token.headers())
        # Behind oauth2-proxy (Keycloak): without the session cookie we get a redirect to the login page
        if self.REDIRECT in response.url:
            self.connect()
            response = self.s.request(method, url, data=data)
        # The API checks tokens itself (AUTH_MODE 'oidc'): log in when someone is at the terminal
        if response.status_code == 401 and response.headers.get('WWW-Authenticate', '').startswith('Bearer'):
            if not self.token.interactive():
                raise NotLoggedInError(f"{self.refusal(response)} (No terminal here to log in from.)")
            self.token.login()
            response = self.s.request(method, url, data=data, headers=self.token.headers())
            if response.status_code == 401:
                raise NotLoggedInError(self.refusal(response))
        if response.status_code == 403:
            raise NotAllowedError(self.refusal(response))

        return self.maybe_json(response.text)

    def get(self, path):
        return self.request('GET', path)

    def post(self, path, data):
        return self.request('POST', path, data=data)


class Pt_Cli(OAuthNego):
    """
    The cli always connect to a specific project, convenience method can be implemented here.
    """
    def __init__(self, project_id, user, password, quiet, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_id = project_id
        self.user = user
        self.password = password
        self.quiet = quiet

    def projects(self):
        return self.get("project")

    def vocabulary(self):
        return self.get("vocabulary")

    def help(self):
        return self.get("help")
