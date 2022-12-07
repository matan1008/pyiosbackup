class PyIosBackupException(Exception):
    """ Domain exception """
    pass


class BackupPasswordIsRequired(PyIosBackupException):
    """ Raise when a password is not supplied for an encrypted backup. """


class MissingEntryError(PyIosBackupException):
    """ Raise when trying to access an entry that doesn't exist. """
    pass
