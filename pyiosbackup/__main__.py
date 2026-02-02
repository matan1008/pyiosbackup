import logging
import pprint

import click

from pyiosbackup import Backup

logger = logging.getLogger('pyiosbackup')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
logger.addHandler(ch)


def set_verbosity(_ctx, _param, value):
    if value > 0:
        logger.setLevel(logging.DEBUG)


backup_path_argument = click.argument('backup_path', type=click.Path(exists=True))
password_argument = click.argument('password')
password_option = click.option('-p', '--password', default='')
target_option = click.option('--target', type=click.Path(), default='.')
strict_option = click.option('--strict', is_flag=True)
verbosity = click.option('-v', '--verbosity', count=True, callback=set_verbosity, expose_value=False)


@click.group()
def cli():
    pass


@cli.command()
@backup_path_argument
@click.argument('domain')
@click.argument('relative_path')
@password_option
@target_option
@strict_option
@verbosity
def extract_domain_path(backup_path, domain, relative_path, password, target, strict):
    """ Extract a file from backup, given its domain and relative path."""
    backup = Backup.from_path(backup_path, password)
    backup.extract_domain_and_path(domain, relative_path, target, strict)


@cli.command()
@backup_path_argument
@click.argument('file_id')
@password_option
@target_option
@strict_option
@verbosity
def extract_id(backup_path, file_id, password, target, strict):
    """ Extract a file from backup, given its file ID."""
    backup = Backup.from_path(backup_path, password)
    backup.extract_file_id(file_id, target, strict)


@cli.command()
@backup_path_argument
@password_argument
@target_option
@strict_option
@verbosity
def extract_all(backup_path, password, target, strict):
    """ Decrypt all files in a backup."""
    backup = Backup.from_path(backup_path, password)
    backup.extract_all(target, strict)


@cli.command()
@backup_path_argument
@password_argument
@target_option
@strict_option
@verbosity
def unback(backup_path, password, target, strict):
    """ Decrypt all files in a backup to a filesystem layout."""
    backup = Backup.from_path(backup_path, password)
    backup.unback(target, strict)


@cli.command()
@backup_path_argument
@password_option
@verbosity
def stats(backup_path, password):
    """ Show statistics about a backup."""
    backup = Backup.from_path(backup_path, password)
    pprint.pprint(backup.stats())


def main():
    cli()


if __name__ == '__main__':
    main()
