#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2015 C de-Avillez <hggdh2@ubuntu.com>
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MErcHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import sys
import os.path
import unittest
import subprocess

myPath = os.path.dirname(__file__)
sys.path.insert(0, os.path.realpath(os.path.join(myPath, "..", "../bin", "../lib")))


# from pasaffe_lib.readdb import PassSafeFile


def cliCmd():
    return "%s/../bin/pasaffe-cli" % myPath


def subproc(command, test):
    rc = 0
    result = None
    try:
        result = subprocess.check_output(command).splitlines()  # pylint: disable=E1103
    except subprocess.CalledProcessError as err:
        print("%s failed with rc=%s" % (test, err.returncode))
        print("%s" % err.output)
        rc = err.returncode
    return result, rc


def gen_pswd(size=16):
    command = ("%s" % cliCmd(), "--genpswd", "--pswdlen=%s" % size)
    rc = 0
    db_pswd, rc = subproc(command, "gen_pswd")
    if rc == 0:
        db_pswd = db_pswd[0].decode('utf-8').strip()
    return db_pswd, rc


def createDB(filename, password):
    command = (cliCmd(), "--createdb", "--masterpassword=%s" % password,
               "--file=%s" % filename)
    rc = 0
    result, rc = subproc(command, "createDB")
    return result, rc


def addEntry(db, pswd, entry=None, group=None, userid=None, password=None, url=None, notes=None):
    command = []
    command.append(cliCmd())
    command.append("--debug")
    command.append("--add")
    command.append("--file=%s" % db)
    command.append("--masterpassword=%s" % pswd)
    command.append("--entry=%s" % entry)
    if group is not None:
        command.append("--group=%s" % group)
    if userid is not None:
        command.append("--user=%s" % userid)
    if password is not None:
        command.append("--pswd=%s" % password)
    if url is not None:
        command.append("--url=%s" % url)
    if notes is not None:
        command.append("--notes=%s" % notes)
    rc = 0
    result = None
    print("command=%s" % command)
    result, rc = subproc(command, "addEntry")
    return result, rc


def replEntry(db, pswd, entry=None, newentry=None, group=None, userid=None, password=None, url=None, notes=None):
    command = []
    command.append(cliCmd())
    command.append("--debug")
    command.append("--repl")
    command.append("--file=%s" % db)
    command.append("--masterpassword=%s" % pswd)
    command.append("--entry=%s" % entry)
    if newentry is not None:
        command.append("--newentry=%s" % newentry)
    if group is not None:
        command.append("--group=%s" % group)
    if userid is not None:
        command.append("--user=%s" % userid)
    if password is not None:
        command.append("--pswd=%s" % password)
    if url is not None:
        command.append("--url=%s" % url)
    if notes is not None:
        command.append("--notes=%s" % notes)
    rc = 0
    result = None
    print("command=%s" % command)
    result, rc = subproc(command, "replEntry")
    return result, rc


def listEntry(db, pswd, entry="Dummy", fuzzy=False, listUserId=False, listPswd=False, listGroup=False, listURL=False,
              listNotes=False, listAll=False):
    command = []
    command.append(cliCmd())
    command.append("--debug")
    command.append("--file=%s" % db)
    command.append("--masterpassword=%s" % pswd)
    command.append("--entry=%s" % entry)
    if listAll:
        command.append("--listall")
    else:
        command.append("--list")
        if fuzzy:
           command.append("--fuzzy")
        if listUserId:
           command.append("--listuser")
        if listGroup:
           command.append("--listgroup")
        if listPswd:
           command.append("--listpswd")
        if listURL:
           command.append("--listurl")
        if listNotes:
           command.append("--listnotes")
    rc = 0
    result = None
    print("command=%s" % command)
    result, rc = subproc(command, "listEntry")
    return result, rc



class TestPasaffeCLI(unittest.TestCase):
    def csetUp(self):
        pass

    def test_t01GenPassword(self):
        Len = 8
        while Len < 32:
            password, rc = gen_pswd(size=Len)
            self.assertEqual(rc, 0, msg="call to genpswd failed")
            self.assertNotEqual(len(password), 0, msg="Failed to generate a password")
            self.assertEqual(len(password), Len, msg="Length of generated password does not match requested length")
            Len += 1

    def test_t02createDB(self):
        db_pswd, rc = gen_pswd()
        self.assertEqual(rc, 0, msg="call to genpswd failed")
        db_name = "/tmp/test_pasaffe-cli.psafe3"
        if os.path.isfile(db_name):
            os.remove(db_name)
        result, rc = createDB(db_name, db_pswd)
        self.assertEqual(rc, 0, msg="DB creation failed")
        self.assertTrue(os.path.isfile(db_name))
        os.remove(db_name)

    def test_t03addEntry(self):
        db_pswd, rc = gen_pswd()
        self.assertEqual(rc, 0, msg="call to genpswd failed")
        db_name = "/tmp/test_pasaffe-cli.psafe3"
        result, rc = createDB(db_name, db_pswd)
        self.assertEqual(rc, 0, msg="DB creation failed")
        result, rc = addEntry(db_name, db_pswd, entry="Entry1")
        self.assertNotEqual(rc, 0)
        result, rc = addEntry(db_name, db_pswd, entry="Entry2", group="Group2")
        self.assertNotEqual(rc, 0)
        result, rc = addEntry(db_name, db_pswd, entry="Entry3", group="Group3", userid="User3")
        self.assertEqual(rc, 0)
        result, rc = addEntry(db_name, db_pswd, entry="Entry4", group="Group4", userid="User4", password="Password4")
        self.assertEqual(rc, 0)
        result, rc = addEntry(db_name, db_pswd, entry="Entry5", group="Group5", userid="User5", password="Password5",
                              url="http://127.0.0.1")
        self.assertEqual(rc, 0)
        result, rc = addEntry(db_name, db_pswd, entry="Entry6", group="Group6", userid="User6", password="Password6",
                              url="http://127.0.0.1", notes="This is a note for entry6")
        self.assertEqual(rc, 0)
        os.remove(db_name)

    def test_t04replaceEntry(self):
        db_pswd, rc = gen_pswd()
        self.assertEqual(rc, 0, msg="call to genpswd failed")
        db_name = "/tmp/test_pasaffe-cli.psafe3"
        result, rc = createDB(db_name, db_pswd)
        self.assertEqual(rc, 0, msg="DB creation failed")
        result, rc = addEntry(db_name, db_pswd, entry="Entry1", group="Group1", userid="User1")
        self.assertEqual(rc, 0, msg="adding entry 1 failed")
        result, rc = replEntry(db_name, db_pswd, entry="Entry1", newentry="NewEntry1")
        self.assertEqual(rc, 0, msg="replacing entry string failed")
        result, rc = replEntry(db_name, db_pswd, entry="NewEntry1", group="NewGroup1")
        self.assertEqual(rc, 0, msg="replacing group string failed")
        result, rc = replEntry(db_name, db_pswd, entry="NewEntry1", group="Group1", userid="NewUser1")
        self.assertEqual(rc, 0, msg="replacing user string failed")
        result, rc = replEntry(db_name, db_pswd, entry="NewEntry1", group="Group1", userid="User1",
                               password="Password1")
        self.assertEqual(rc, 0, msg="replacing password string failed")
        result, rc = replEntry(db_name, db_pswd, entry="NewEntry1", group="Group1", userid="User1",
                               password="Password1", url="http://127.0.0.1")
        self.assertEqual(rc, 0, msg="replacing URL string failed")
        result, rc = replEntry(db_name, db_pswd, entry="NewEntry1", group="Group1", userid="User1",
                               password="Password1", url="http://127.0.0.1",
                               notes="This is a note for newEntry1")
        self.assertEqual(rc, 0, msg="replacing notes string failed")
        os.remove(db_name)


def test_t05listEntry(self):
    db_pswd, rc = gen_pswd()
    self.assertEqual(rc, 0, msg="call to genpswd failed")
    db_name = "/tmp/test_pasaffe-cli.psafe3"
    result, rc = createDB(db_name, db_pswd)
    self.assertEqual(rc, 0, msg="DB creation failed")
    result, rc = addEntry(db_name, db_pswd, entry="Entry1", group="Group1", userid="User1",
                           password="Password1", url="http://127.0.0.1",
                           notes="This is a note for Entry1")
    self.assertEqual(rc, 0, msg="adding entry 1 failed")
    result, rc = addEntry(db_name, db_pswd, entry="Entry2", group="Group2", userid="User2",
                           password="Password2", url="http://127.0.0.2",
                           notes="This is a note for Entry2")
    self.assertEqual(rc, 0, msg="adding entry 2 failed")
    result, rc = addEntry(db_name, db_pswd, entry="Entry2", group="Group2", userid="User2",
                           password="Password3", url="http://127.0.0.3",
                           notes="This is a note for Entry3")
    self.assertEqual(rc, 0, msg="adding entry 3 failed")
    result, rc = listEntry(db_name, db_pswd, entry="Entry1")
    self.assertEqual(rc, 0, "list Entry1 failed")
    os.remove(db_name)


def test_t06removeEntry(self):
    pass


if __name__ == '__main__':
    unittest.main()
