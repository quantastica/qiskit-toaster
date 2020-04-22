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
from quantastica.qiskit_toaster import ToasterJob
from quantastica import qconvert
from qiskit.providers import BaseBackend
from qiskit.providers.models import BackendConfiguration


class ToasterBackend(BaseBackend):

    DEFAULT_TOASTER_HOST = ToasterJob.ToasterJob.DEFAULT_TOASTER_HOST
    DEFAULT_TOASTER_PORT = ToasterJob.ToasterJob.DEFAULT_TOASTER_PORT

    MAX_QUBITS_MEMORY = 32
    DEFAULT_CONFIGURATION = {
        "backend_name": "toaster_simulator",
        "backend_version": "1.0.0",
        "n_qubits": MAX_QUBITS_MEMORY,
        "url": "https://quantastica.com/",
        "simulator": True,
        "local": True,
        "conditional": False,
        "open_pulse": False,
        "memory": True,
        "max_shots": 65536,
        "description": "An q-toaster based qasm simulator",
        "coupling_map": None,
        "basis_gates": qconvert.supported_gates(),
        "gates": [],
    }

    def __init__(
        self,
        configuration=None,
        provider=None,
        backend_name=None,
        toaster_host=None,
        toaster_port=None,
        use_cli=False,
    ):
        configuration = configuration or BackendConfiguration.from_dict(
            self.DEFAULT_CONFIGURATION
        )

        # disable unroller
        # configuration.basis_gates=None

        super().__init__(configuration=configuration, provider=provider)

        getstates = False
        if (
            backend_name is not None
            and backend_name == "statevector_simulator"
        ):
            getstates = True

        self._getstates = getstates
        self._toaster_port = (
            toaster_port or ToasterBackend.DEFAULT_TOASTER_PORT
        )
        self._toaster_host = (
            toaster_host or ToasterBackend.DEFAULT_TOASTER_HOST
        )
        self._use_cli = use_cli

    # @profile
    def run(self, qobj, backend_options=None):
        job_id = str(uuid.uuid4())
        job = ToasterJob.ToasterJob(
            self,
            job_id,
            qobj,
            getstates=self._getstates,
            toaster_host=self._toaster_host,
            toaster_port=self._toaster_port,
            backend_options=backend_options,
            use_cli=self._use_cli,
        )
        job.submit()
        return job

    @staticmethod
    def name():
        return "qubit_toaster"


def get_backend(
    backend_name=None, toaster_host=None, toaster_port=None, use_cli=False
):
    return ToasterBackend(
        backend_name=backend_name,
        toaster_host=toaster_host,
        toaster_port=toaster_port,
        use_cli=use_cli,
    )
