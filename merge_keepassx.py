#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set fileencoding=utf8

import argparse
import functools
from datetime import datetime
from xml.etree import ElementTree
from itertools import groupby, ifilter, chain, imap


class Entry(object):

    def __init__(self, group, tree):
        self._date_format = "%Y-%m-%dT%H:%M:%S"
        self._group = group
        self._tree = tree

    @property
    def tree(self):
        return self._tree

    @property
    def group(self):
        return self._group

    @property
    def title(self):
        return self._tree.find('title').text

    @property
    def username(self):
        return self._tree.find('username').text

    @property
    def lastmod(self):
        text = self._tree.find('lastmod').text
        return datetime.strptime(text, self._date_format)


class Group(object):

    def __init__(self, tree):
        self._tree = tree

    @property
    def title(self):
        return self._tree.find('title').text

    @property
    def entries(self):
        build_entry = functools.partial(Entry, self)
        return imap(build_entry, self._tree.findall('entry'))


def get_entries(filename):
    tree = ElementTree.parse(filename).getroot()
    groups = imap(Group, tree.findall('group'))

    def not_backup(group):
        return group.title != 'Backup'

    groups = ifilter(not_backup, groups)

    for group in groups:
        for entry in group.entries:
            yield entry


def main():
    parser = argparse.ArgumentParser(description="Merge keepassx databases.")

    parser.add_argument('infilenames', nargs='*')
    parser.add_argument('outfilename')

    args = parser.parse_args()

    ####################################
    # Get and sort all of the entries. #
    ####################################

    entries = chain(*[get_entries(fname) for fname in args.infilenames])

    def entry_key(entry):
        return (entry.group.title, entry.title, entry.username)

    entries = sorted(entries, key=entry_key)

    groups = (group for _, group in groupby(entries, key=entry_key))

    def latest_entry(group):
        return max(group, key=lambda entry: entry.lastmod)

    entries = (latest_entry(group) for group in groups)

    #############################################
    # Build and write the merged database file. #
    #############################################

    def build_group(title, entries):
        group = ElementTree.Element('group')
        title_element = ElementTree.SubElement(group, 'title')
        title_element.text = title
        group.extend((entry.tree for entry in entries))
        return group

    def group_key(entry):
        return entry.group.title

    groups = (build_group(k, g) for k, g in groupby(entries, key=group_key))

    database = ElementTree.Element('database')
    database.extend(groups)
    ElementTree.ElementTree(database).write(args.outfilename)


if __name__ == '__main__':
    main()
