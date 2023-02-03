import getpass
import json
import pathlib
import pickle
import re
import weakref

import requests





class OAuthNego():

    CSRF = "_oauth2_proxy_csrf"
    REDIRECT = 'redirect_uri'
    AUTH_SESSION_ID = 'AUTH_SESSION_ID'
    AUTH_SESSION_ID_LEGACY = 'AUTH_SESSION_ID_LEGACY'
    KC_RESTART = 'KC_RESTART'
    PARAMS = ['session_code', 'execution', 'client_id', 'tab_id']

    def __init__(self, root, session_file):
        self.root = root
        self.cookies = {}
        self.r_get = None
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

    def connect(self):
        """
        This is pretty specific to keycloak,
        need to find somthing more specific for when we will
        use CAF or cilogon
        :return:
        """
        params = {}
        for k in self.PARAMS:
            params[k] = re.search('{}=(.*?)&'.format(k).encode(),
                                  self.r_get.content).groups()[0].decode()
        post_url = re.search('(https://.*?)\?'.format(k).encode(),
                             self.r_get.content).groups()[0].decode()
        return self.s.post(post_url, params=params, data=self.prompt_pw())

    def maybe_json(self, data):
        try:
            return json.loads(data)
        except json.decoder.JSONDecodeError:
            return data

    def get(self, path):
        url = "{}/{}".format(self.root, path)
        self.r_get = self.s.get(url)
        # If the api is protected and the session is does
        # not have the requires token or cookie
        # we get a redirect
        if self.REDIRECT in self.r_get.url:
            r_connect = self.connect()
            return self.maybe_json(r_connect.text)

        return self.maybe_json(self.r_get.text)


    def create_project(self, name):
        path = f'project/create/{name}'
        return self.get(path=path)


if __name__ == '__main__':
    import yaml
    with open('connect.yaml') as fp:
        config = yaml.load(fp, Loader=yaml.SafeLoader)

    session_file = pathlib.Path(config['session_file']).expanduser()
    connect = OAuthNego(config['url_root'], session_file=session_file)

    data = connect.get('')
    print(data)
    data = connect.create_project('new_project')
    print(data)
