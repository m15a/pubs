import sys
import io
import os
import shutil
import glob

import dotdot

from pyfakefs import fake_filesystem, fake_filesystem_unittest

from pubs.p3 import input, _fake_stdio, _get_fake_stdio_ucontent
from pubs import content, filebroker

# code for fake fs

real_os      = os
real_os_path = os.path
real_open    = open
real_shutil  = shutil
real_glob    = glob
real_io      = io


# capture output

def capture(f, verbose=False):
    """Capture the stdout and stderr output.

    Useful for comparing the output with the expected one during tests.

    :param f:        The function to capture output from.
    :param verbose:  If True, print call will still display their outputs.
                     If False, they will be silenced.

    """
    def newf(*args, **kwargs):
        old_stderr, old_stdout = sys.stderr, sys.stdout
        sys.stdout = _fake_stdio(additional_out=old_stderr if verbose else None)
        sys.stderr = _fake_stdio(additional_out=old_stderr if False else None)
        try:
            return f(*args, **kwargs), _get_fake_stdio_ucontent(sys.stdout), _get_fake_stdio_ucontent(sys.stderr)
        finally:
            sys.stderr, sys.stdout = old_stderr, old_stdout
    return newf


# Test helpers

# automating input
real_input = input


class FakeInput():
    """ Replace the input() command, and mock user input during tests

        Instanciate as :
        input = FakeInput(['yes', 'no'])
        then replace the input command in every module of the package :
        input.as_global()
        Then :
        input() returns 'yes'
        input() returns 'no'
        input() raises IndexError
     """

    class UnexpectedInput(Exception):
        pass

    def __init__(self, inputs, module_list=tuple()):
        self.inputs = list(inputs) or []
        self.module_list = module_list
        self._cursor = 0

    def as_global(self):
        for md in self.module_list:
            md.input = self
            if md.__name__ == 'pubs.uis':
                md.InputUI.editor_input = self
                md.InputUI.edit_file = self.input_to_file
                # Do not catch UnexpectedInput
                original_handler = md.InputUI.handle_exception

                def handler(ui, exc):
                    if isinstance(exc, self.UnexpectedInput):
                        raise
                    else:
                        original_handler(ui, exc)

                md.InputUI.handle_exception = handler

    def input_to_file(self, path_to_file, temporary=True):
        content.write_file(path_to_file, self())

    def add_input(self, inp):
        self.inputs.append(inp)

    def __call__(self, *args, **kwargs):
        try:
            inp = self.inputs[self._cursor]
            self._cursor += 1
            return inp
        except IndexError:
            raise self.UnexpectedInput('Unexpected user input in test.')


class TestFakeFs(fake_filesystem_unittest.TestCase):

    def setUp(self):
        self.rootpath = os.path.abspath(os.path.dirname(__file__))
        self.setUpPyfakefs()
        self.fs.CreateDirectory(os.path.expanduser('~'))
        self.fs.CreateDirectory(self.rootpath)
        os.chdir(self.rootpath)

    def reset_fs(self):
        self._stubber.tearDown()  # renew the filesystem
        self.setUp()
