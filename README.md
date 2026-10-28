# pt-cli

pt-cli is the C3G database [client](https://github.com/c3g/project_tracking_cli). It communicates with [project tracking](https://github.com/c3g/project_tracking), the C3G database API.

Python 3.11 or newer is required. The default development version is 3.14 (`.python-version`); CI tests 3.11 to 3.14.

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

Commands working on one project need it: give `--project`, or set `project:` in `./connect.yaml` or
`~/.config/pt_cli/connect.yaml`. There is no default project. `ingest` commands without one use the
`project_name` of the JSON. Project names are matched ignoring case, so `--project my-project` finds `MY-PROJECT`.

```bash
pt-cli --url-root https://c3g-portal.dev-sd4h.ca --project MY-PROJECT ingest run_processing --input-json run_processing.json
```

To list the values the server accepts for controlled fields, run this command. It shows the enum values
(e.g. `readset_state`, `readset_lane`) and the analysis operations accepted by `ingest analysis`
(`operation_name`, `operation_pipeline`, `operation_protocol`):

```bash
pt-cli --url-root https://c3g-portal.dev-sd4h.ca vocabulary
```


To write one [nf-core/oncoanalyser samplesheet](https://nf-co.re/oncoanalyser/latest/docs/usage/#samplesheet)
per sample group, `<group>.samplesheet.csv`, for every group of the given specimens or the named groups,
DNA and RNA together unless you give `--nucleic_acid_type`:

```bash
pt-cli --url-root https://c3g-portal.dev-sd4h.ca --project MY-PROJECT digest oncoanalyser_samplesheet --specimen_name SPECIMEN-1 --endpoint abacus -o samplesheets/
pt-cli --url-root https://c3g-portal.dev-sd4h.ca --project MY-PROJECT digest oncoanalyser_samplesheet --sample_group_name SPECIMEN-1_G1 --endpoint abacus
```

To list and edit the groups of samples analysed together (declared with `sample_group_name` at ingestion):

```bash
pt-cli --url-root https://c3g-portal.dev-sd4h.ca --project MY-PROJECT sample_group list --specimen_name SPECIMEN-1
# The groups a sample belongs to
pt-cli --url-root https://c3g-portal.dev-sd4h.ca --project MY-PROJECT sample_group list --sample_name SAMPLE-1-1RT
# Add samples (creates the group when it doesn't exist) and/or remove samples; a group left empty is deleted
pt-cli --url-root https://c3g-portal.dev-sd4h.ca --project MY-PROJECT sample_group edit --name SPECIMEN-1_G1 --add SAMPLE-1-1RT
pt-cli --url-root https://c3g-portal.dev-sd4h.ca --project MY-PROJECT sample_group edit --name SPECIMEN-1_G1 --remove SAMPLE-1-1DN
# Rename a group (its id is in 'sample_group list'); deprecate, delete and curate work the same way
pt-cli --url-root https://c3g-portal.dev-sd4h.ca --project MY-PROJECT --data '{"modification": [{"table": "sample_group", "id": [1], "column": "name", "new": "SPECIMEN-1_G3"}]}' edit
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