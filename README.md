# pt-cli

pt-cli is the C3G database [client](https://github.com/c3g/project_tracking_cli). It communicates with [project tracking](https://github.com/c3g/project_tracking), the C3G database API.

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

To access a route from the `help` command list, for example `/project`, run this command:
```bash 
pt-cli --url-root https://c3g-portal.dev-sd4h.ca route /project
```

The `route` command selects the HTTP method:
- `POST`, when you give `--data` or `--data-file`
- `GET`, in all other cases

If an endpoint needs a specific HTTP verb, you can set it with `--method`.

```bash
# Force POST even without a payload
pt-cli --url-root https://c3g-portal.dev-sd4h.ca route /admin/create_project/cphi-test --method POST

# Explicit GET
pt-cli --url-root https://c3g-portal.dev-sd4h.ca route /project --method GET
```

To create a project with optional JSON metadata, use the dedicated command:

```bash
# Create/fetch project by name only
pt-cli --url-root https://c3g-portal.dev-sd4h.ca admin create-project --name cphi-test

# Create/fetch project with external metadata sent as JSON body
pt-cli --url-root https://c3g-portal.dev-sd4h.ca admin create-project --name cphi-test --ext-id 123 --ext-src lims
```

Equivalent raw route form:

```bash
pt-cli --url-root https://c3g-portal.dev-sd4h.ca --data '{"ext_id":123,"ext_src":"lims"}' route /admin/create_project/cphi-test --method POST
```


## Test the client on a local server (developer mode)
Install pt-cli in dev mode, with pip's `-e` option. This mode applies your source code changes to the installation automatically.
```bash
git clone https://github.com/c3g/project_tracking_cli
cd project_tracking_cli/
python -m venv venv
source venv/bin/activate
pip install -e .
pt-cli -h
```

After you start a [project_tracking server on your local machine](https://github.com/c3g/project_tracking#from-github-with-sqlite-best-for-developer), you can test the client and add new features.

```bash
# Printing all routes
pt-cli --url-root http://127.0.0.1:5000 help
# Creating a project named my-project
pt-cli --url-root http://127.0.0.1:5000 route /admin/create_project/my-project --method POST
# Creating a project with metadata
pt-cli --url-root http://127.0.0.1:5000 admin create-project --name my-project --ext-id 1 --ext-src lims
# Should return
# {"creation": "2023-04-13T13:50:39.781030", "id": 1, "name": "MY-PROJECT", "tablename": "project"}
# Checking what projects are available
pt-cli --url-root http://127.0.0.1:5000  route project
# Should return
# {"Projetc list": ["MY-PROJECT"]}
```

## Tab completion

```bash
# Generating completion file for bash
pt-cli -s bash > _pt-cli
# Generating completion file for zsh
pt-cli -s zsh > _pt-cli
# For oh-my-zsh users
pt-cli -s zsh > ~/.oh-my-zsh/completions/_pt-cli
```
After you generate the file, run `source` on it to enable tab completion. If you use oh-my-zsh, reload your environment instead.