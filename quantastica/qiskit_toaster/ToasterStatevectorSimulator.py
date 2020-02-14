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


from .ToasterBackend import ToasterBackend

class ToasterStatevectorSimulator(ToasterBackend):
    def __init__(self, configuration=None, 
                provider=None,
                toasterpath=None):
        super().__init__(
            configuration=configuration, 
            provider=provider,
            toasterpath=toasterpath,
            backend_name="statevector_simulator")

    @staticmethod
    def name():
        return 'statevector_simulator'
