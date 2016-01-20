# Copyright ClusterHQ Inc.  See LICENSE file for details.

"""
Find and report on tests marked as flaky.
"""

import sys

from testtools import iterate_tests
from twisted.python.reflect import namedAny
from twisted.python.usage import Options, UsageError
from twisted.trial.runner import ErrorHolder, TestLoader

from flocker.testtools._flaky import _get_flaky_annotation


class FindFlakyTestsOptions(Options):
    """
    Options for finding flaky tests.
    """

    def parseArgs(self, *suites):
        """
        Accept an arbitrary number of suites, specified as fully-qualified
        Python names.
        """
        self['suites'] = suites


def _load_tests(name):
    """
    Find all the tests under ``name``.

    :param str name: The fully-qualified Python name of an object.
    :return: A ``TestSuite`` or ``TestCase`` containing all the tests.
    """
    loader = TestLoader()
    return loader.loadByName(name, recurse=True)


def _iter_tests(names):
    """
    Given a list of names, iterate through all the tests in them.
    """
    for name in names:
        suite = _load_tests(name)
        for test in iterate_tests(suite):
            yield test


def get_flaky_annotation(case):
    """
    Given a test, return the flaky annotation object.

    If the test failed to load somehow (i.e. was an ``ErrorHolder``),
    re-raise the reason it failed to load.
    """
    error = getattr(case, 'error', None)
    if error:
        raise error[0], error[1], error[2]
    return _get_flaky_annotation(case)


def find_flaky_tests(suites):
    """
    Find all flaky tests in the given suites.
    """
    for test in _iter_tests(suites):
        annotation = get_flaky_annotation(test)
        if annotation:
            yield test, annotation


def report_flaky_tests(output, flaky_tests):
    """
    Report on flaky tests.
    """
    for test in flaky_tests:
        output.write('{}\n'.format(test))


def find_flaky_tests_main(args, base_path, top_level, stdout=None,
                          stderr=None):
    """
    Find and report on tests marked as flaky.
    """
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    # XXX: Boilerplate copied from release.py, very similar (but not similar
    # enough!) to boilerplate in flocker.common.script.
    options = FindFlakyTestsOptions()
    try:
        options.parseOptions(args)
    except UsageError as e:
        stderr.write("{}: {}\n".format(base_path.basename(), e))
        sys.exit(1)

    flaky_tests = find_flaky_tests(options['suites'])
    report_flaky_tests(stdout, flaky_tests)
