# pt-cli

This is the c3g database [client](https://github.com/c3g/project_tracking_cli)  to talk with [project tracking](https://github.com/c3g/project_tracking), the c3g database api!

To install:

```bash
git clone https://github.com/c3g/project_tracking_cli
cd project_tracking_cli/
python -m venv venv
source venv/bin/activate
pip install .
pt-cli -h
```


To query the api at c3g-portal.dev-sd4h.ca:

```bash
pt-cli --url-root https://c3g-portal.dev-sd4h.ca help
```

To access one of the routes listed with the `help` cmd, here `/project`
```bash 
pt-cli --url-root https://c3g-portal.dev-sd4h.ca route /project
```


## Test the client on a local server (developer mode)
Make sure that you are installing pt-cli in dev mode (pip's `-e` option), so the source code modifications are reflected automatically in the installation
```bash
git clone https://github.com/c3g/project_tracking_cli
cd project_tracking_cli/
python -m venv venv
source venv/bin/activate
pip install -e .
pt-cli -h
```

Once you have a [project_tracking server running on your local machine](https://github.com/c3g/project_tracking#from-github-with-sqlite-best-for-developer) you can test that the client is working properly and add features to it.

```bash
# Printing all routes
pt-cli --url-root http://127.0.0.1:5000 help
# Creating a project named my-project
pt-cli --url-root http://127.0.0.1:5000  route /admin/create_project/my-project
# Should return
# {"creation": "2023-04-13T13:50:39.781030", "id": 1, "name": "MY-PROJECT", "tablename": "project"}
# Checking what projects are available
pt-cli --url-root http://127.0.0.1:5000  route project
# Should return
# {"Projetc list": ["MY-PROJECT"]}
```

## Having <TAB> completion

```bash
# Generating completion file for bash
pt-cli -s bash > _pt-cli
# Generating completion file for zsh
pt-cli -s zsh > _pt-cli
# For oh-my-zsh users
pt-cli -s zsh > ~/.oh-my-zsh/completions/_pt-cli
```
Once done `source` the file created (or reload your environment for omz users) to have completion enabled.