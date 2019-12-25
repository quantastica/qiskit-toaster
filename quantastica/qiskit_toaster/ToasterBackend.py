# This code is part of quantastica.qiskit_toaster
#
# (C) Copyright Quantastica 2019. 
# https://quantastica.com/
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import uuid
import logging
import time
from collections import Counter

import numpy as np
from quantastica.qiskit_toaster import ToasterJob
from qiskit.providers import BaseBackend
from qiskit.result import Result
from qiskit.providers.models import BackendConfiguration
import os

class ToasterBackend(BaseBackend):
    MAX_QUBITS_MEMORY = 32

    DEFAULT_CONFIGURATION = {'backend_name': 'toaster_simulator',
                             'backend_version': '1.0.0',
                             'n_qubits': MAX_QUBITS_MEMORY,
                             'url': 'https://quantastica.com/',
                             'simulator': True,
                             'local': True,
                             'conditional': False,
                             'open_pulse': False,
                             'memory': True,
                             'max_shots': 65536,
                             'description': 'An q-toaster based qasm simulator',
                             'coupling_map': None,
                             'basis_gates': ['u1',
                                             'u2',
                                             'u3',
                                             'cx',
                                             'id',
                                             'x',
                                             'y',
                                             'z',
                                             'h',
                                             's',
                                             't'],
                             'gates': []}

    def __init__(self, configuration=None, 
                provider=None,
                backend_name = None, 
                toasterpath=None):
        configuration = configuration or BackendConfiguration.from_dict(
            self.DEFAULT_CONFIGURATION)
        super().__init__(configuration=configuration, provider=provider)

        getstates = False
        if backend_name is not None and backend_name == "statevector_simulator":
            getstates = True

        self._getstates = getstates
        self._configuration = configuration
        self._number_of_qubits = None
        self._number_of_cbits = None
        self._statevector = None
        self._results = {}
        self._shots = {}
        self._local_random = np.random.RandomState()
        self._sample_measure = False
        self._chop_threshold = 15  # chop to 10^-15
        self._toasterpath = toasterpath or os.getenv('TOASTERPATH') or "qubit-toaster"

    #@profile
    def run(self, qobj):
        job_id = str(uuid.uuid4())
        job = ToasterJob.ToasterJob(self, job_id, qobj, 
                                    self._toasterpath,
                                    getstates=self._getstates)
        job.submit()
        return job


    @staticmethod
    def name():
        return 'qubit_toaster'

def get_backend(backend_name = None, toasterpath = None):
        return ToasterBackend(backend_name = backend_name, toasterpath = toasterpath)
