class PyIosBackupException(Exception):
    """ Domain exception """
    pass


class BackupPasswordIsRequired(PyIosBackupException):
    """ Raise when a password is not supplied for an encrypted backup. """
