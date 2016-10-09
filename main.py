#!/usr/bin/env python

import argparse
import logging
import sys

from label.label import FileWalker, ImageLabeler, LabelServiceExecutor, GoogleServiceConnector


def _checked_load_logging_config(config_path):
    from os import path
    import logging.config
    expanded_config_path = path.expanduser(config_path)
    if not path.exists(expanded_config_path):
        raise Exception(
            "failed to locate a logging configuration at [%s]. please check the location" % expanded_config_path)
    logging.config.fileConfig(expanded_config_path)


def main(options):
    if options.verbose > 1:
        _checked_load_logging_config("~/.python/logging_debug.conf")
    elif options.verbose:
        _checked_load_logging_config("~/.python/logging.conf")

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    file_walker = FileWalker(ImageLabeler(), LabelServiceExecutor(GoogleServiceConnector()))
    file_walker.walk_and_tag(args.root_directory)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root_directory', help='directory to start scanning for files')
    parser.add_argument('-v', '--verbose', dest='verbose', help='print status messages to stdout more verbose',
                        action='count')
    args = parser.parse_args()
    main(args)
