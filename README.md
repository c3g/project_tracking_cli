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
