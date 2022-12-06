class PyIosBackupException(Exception):
    """ Domain exception """
    pass


class BackupPasswordIsRequiredError(PyIosBackupException):
    """ Raise when a password is not supplied for an encrypted backup. """
    pass


class NonExistentEntryError(PyIosBackupException):
    """ Raise when attempting to create an invalid entry """
    pass
