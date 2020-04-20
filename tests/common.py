import os
from quantastica.qiskit_toaster import ToasterBackend
import logging
import unittest
import sys
import time


class TestToasterBase(unittest.TestCase):
    @staticmethod
    def toaster_backend(backend_name=None):
        return ToasterBackend.get_backend(
            backend_name,
            toaster_host=os.getenv("TOASTER_HOST", None),
            toaster_port=os.getenv("TOASTER_PORT", None),
            use_cli=os.getenv("USE_CLI", False),
        )

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(
            format="%(levelname)s %(asctime)s %(pathname)s - %(message)s",
            level=os.environ.get("LOGLEVEL", "CRITICAL"),
        )

    def setUp(self):
        self.startTime = time.time()

    def tearDown(self):
        t = time.time() - self.startTime
        sys.stderr.write(" took %.3fs ... " % (t))
