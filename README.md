[![Python application](https://github.com/matan1008/pyiosbackup/workflows/Python%20application/badge.svg)](https://github.com/matan1008/pyiosbackup/actions/workflows/python-app.yml "Python application action")
[![Pypi version](https://img.shields.io/pypi/v/pyiosbackup.svg)](https://pypi.org/project/pyiosbackup/ "PyPi package")
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/matan1008/pyiosbackup.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/matan1008/pyiosbackup/context:python)

- [Description](#description)
- [Installation](#installation)
- [Usage](#usage)
    * [CLI](#cli)
    * [Python](#python)

# Description

`pyiosbackup` is a utility created in order to parse and decrypt iOS backups.

# Installation

Install the last released version using `pip`:

```shell
python3 -m pip install --user -U pyiosbackup
```

Or install the latest version from sources:

```shell
git clone git@github.com:matan1008/pyiosbackup.git
cd pyiosbackup
python3 -m pip install --user -U -e .
```

# Usage

## CLI

Before decrypting a backup, you need to create one. You can use the amazing
[pymobiledevice3](https://github.com/doronz88/pymobiledevice3) to do that:

```shell
pymobiledevice3 backup2 encryption ON 1234 .
pymobiledevice3 backup2 backup --full .
```

After creating the backup, you can decrypt it:

```shell
pyiosbackup extract-all $BACKUP_FOLDER 1234 --target decrypted
```

You can also extract single files by their domain and relative path:

```shell
pyiosbackup extract-domain-path $BACKUP_FOLDER RootDomain Library/Preferences/com.apple.backupd.plist -p 1234
```

Or by their file id:

```shell
pyiosbackup extract-id $BACKUP_FOLDER a8323a1323d9cad416d8b44d87c8049de1adff25 -p 1234
```

You can also print some metadata about the backup:

```shell
pyiosbackup stats $BACKUP_FOLDER -p 1234
```

## Python

Another way to access the functionality of the package is using python code.

For example, iterating over all files in a backup will look like:

```python
from pyiosbackup import Backup

backup_path = 'BACKUP_PATH'
password = '1234'

backup = Backup.from_path(backup_path, password)
for file in backup.iter_files():
    print(file.filename)
    print(file.last_modified)
```

You can also access a specific file:

```python
import plistlib

from pyiosbackup import Backup

backup_path = 'BACKUP_PATH'
password = '1234'

backup = Backup.from_path(backup_path, password)
backupd_plist = backup.get_entry_by_domain_and_path(
    'RootDomain', 'Library/Preferences/com.apple.backupd.plist'
)
print(plistlib.loads(backupd_plist))
```
