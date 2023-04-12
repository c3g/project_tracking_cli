import getpass
import json
import pickle
import re
import weakref
import logging

import requests

logger = logging.getLogger(__name__)


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
        # Initialise session from file
        self.session_file = session_file
        if session_file.is_file():
            self.s = self.load_session(session_file)
        else:
            self.s = requests.session()
        # save session at the end
        self._finalizer = \
            weakref.finalize(self, self.save_session, self.session_file, self.s)

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
        user = input("Username:")
        passwd = getpass.getpass()
        return {'username': user, 'password': passwd, 'credentialId': ''}

    def connect(self, r_get):
        """
        This is pretty specific to keycloak,
        need to find somthing more specific for when we will
        use CAF or cilogon
        :return:
        """
        params = {}
        decoded_content = r_get.content.decode()
        for k in self.PARAMS:
            params[k] = re.search('{}=(.*?)&'.format(k),
                                  decoded_content).groups()[0]
        post_url = re.search('(https://.*?)\?', decoded_content).groups()[0]
        return self.s.post(post_url, params=params, data=self.prompt_pw())

    def maybe_json(self, data):
        try:
            return json.loads(data)
        except json.decoder.JSONDecodeError:
            return data

    def get(self, path):
        url = "{}/{}".format(self.root, path)
        r_get = self.s.get(url)
        # If the api is protected and the session is does
        # not have the requires token or cookie
        # we get a redirect
        if self.REDIRECT in r_get.url:
            r_get = self.connect(r_get)

        return self.maybe_json(r_get.text)

    def post(self, path, data):
        url = "{}/{}".format(self.root, path)
        r_post = self.s.post(url, data=data)
        # If the api is protected and the session is does
        # not have the requires token or cookie
        # we get a redirect
        if self.REDIRECT in r_post.url:
            r_post = self.connect(r_post)

        return self.maybe_json(r_post.text)


class Pt_Cli(OAuthNego):
    """
    The cli always connect to a specific project, convenience method can be implemented here.
    """
    def __init__(self, project_name, *args, **kwargs):
        super(Pt_Cli, self).__init__(*args, **kwargs)
        self.project_name = project_name

    def create_project(self):
        path = f'admin/create_project/{self.project_name}'
        return self.get(path=path)

    def projects(self):
        return self.get("projects")

    def help(self):
        return self.get("help")





