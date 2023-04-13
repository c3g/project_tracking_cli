# pt-cli
The c3g [pt_cli](https://github.com/c3g/project_tracking_cli) is the 
c3g [project tracking](https://github.com/c3g/project_tracking) client!

To install:

```bash
git clone https://github.com/c3g/project_tracking_cli
cd project_tracking_cli/
python -m venv venv
source venv/bin/activate
pip install .
pt_cli -h
```


To query the api at c3g-portal.dev-sd4h.ca:

```bash
pt_cli --url_root https://c3g-portal.dev-sd4h.ca help
```

To acces on of the route listed with the `help` cmd, here `/project`
```bash 
pt_cli --url_root https://c3g-portal.dev-sd4h.ca route /project
```


## Test the client on a local server (developer mode)
Make sure that you are installing pt_cli in dev mode (pip's `-e` option), so the source code modifications 
are reflected automatically in the installation
```bash
git clone https://github.com/c3g/project_tracking_cli
cd project_tracking_cli/
python -m venv venv
source venv/bin/activate
pip install -e .
pt_cli -h
```

Once you have a [project_tracking server running on your local machine](https://github.com/c3g/project_tracking#from-github-with-sqlite-best-for-developer)
you can test that the client is working properly and add features to it.

```bash
pt_cli --url_root http://localhost:5000/ help
[prints all routes]
pt_cli --url_root http://localhost:5000  route /admin/create_project/my-project
{"creation": "2023-04-13T13:50:39.781030", "id": 1, "name": "MY-PROJECT", "tablename": "project"}
pt_cli --url_root http://localhost:5000  route project
{"Projetc list": ["MY-PROJECT"]}
```
