import os
import subprocess
from os.path import join
from subprocess import CalledProcessError, Popen
from time import sleep

from testfixtures import TempDirectory

from util.file_utils import make_directories_if_necessary


class FakeS3Manager(object):
    '''Encapsulates starting and stopping the FakeS3 server process for tests
    that use it.
    This replaces the code related to TestCaseWithSetup.
    '''
    @classmethod
    def start(cls):
        from brokerage import config
        cls.fakes3_root_dir = TempDirectory()
        bucket_name = config.get('aws_s3', 'bucket')
        make_directories_if_necessary(join(cls.fakes3_root_dir.path,
                                           bucket_name))

        # start FakeS3 as a subprocess
        # redirect both stdout and stderr because it prints all its log
        # messages to both
        cls.fakes3_command = 'fakes3 --port %s --root %s' % (
            config.get('aws_s3', 'port'), cls.fakes3_root_dir.path)

        cls.fakes3_process = Popen(cls.fakes3_command.split(), stderr=subprocess.STDOUT)

        # make sure FakeS3 is actually running (and did not immediately exit
        # because, for example, another instance of it is already
        # running and occupying the same port)
        sleep(1)
        cls.check()

    @classmethod
    def check(cls):
        exit_status = cls.fakes3_process.poll()
        if exit_status is not None:
                raise CalledProcessError(exit_status, cls.fakes3_command)

    @classmethod
    def stop(cls):
        cls.fakes3_process.kill()
        cls.fakes3_process.wait()
        cls.fakes3_root_dir.cleanup()
        exit_status = cls.fakes3_process.poll()
        # don't care if it exited with 0 or not
        assert exit_status is not None
