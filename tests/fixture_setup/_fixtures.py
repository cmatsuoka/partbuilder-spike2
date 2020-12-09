# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-


import fixtures
import os
import shutil
import tempfile


class TempCWD(fixtures.Fixture):
    def __init__(self, rootdir=None):
        super().__init__()
        if rootdir is None and "TMPDIR" in os.environ:
            rootdir = os.environ.get("TMPDIR")
        self.rootdir = rootdir
        self._data_path = os.getenv("PARTBUILDER_TEST_KEEP_DATA_PATH", None)

    def setUp(self):
        """Create a temporary directory an cd into it for the test duration."""
        super().setUp()
        if self._data_path:
            os.makedirs(self._data_path)
            self.path = self._data_path
        else:
            self.path = tempfile.mkdtemp(dir=self.rootdir)
        current_dir = os.getcwd()
        self.addCleanup(os.chdir, current_dir)
        if not self._data_path:
            self.addCleanup(shutil.rmtree, self.path, ignore_errors=True)
        os.chdir(self.path)
