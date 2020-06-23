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
import logging
import subprocess

logger = logging.getLogger(__name__)


class ToasterCliInterface:
    def __init__(self, toaster_path):
        self.toaster_path = toaster_path

    def execute(
        self,
        jsonstr,
        job_id=None,
        seed=None,
        shots=None,
        returns=None,
        optimization=None,
    ):

        args = [self.toaster_path, "-", "-s", str(shots)]
        if returns:
            returns = returns.split(",")
        else:
            returns = ["counts"]
        args.append("-r")
        args += returns

        if seed:
            args.append("--seed")
            args.append(str(seed))
        if optimization:
            args.append("-o")
            args.append(str(optimization))

        proc = subprocess.Popen(
            args,
            close_fds=False,
            restore_signals=False,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        logger.info("Running q-toaster with following params:")
        logger.info(args)
        qtoasterjson, stderr = proc.communicate(input=jsonstr)
        returncode = proc.returncode
        if returncode > 0:
            logger.debug(
                "Toaster finished with non-zero exit code (%d) :" % returncode,
                stderr,
            )
            raise RuntimeError(
                "Error received from CLI, exit code: %d" % returncode
            )

        return qtoasterjson
