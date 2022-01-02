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

from concurrent import futures
import logging
import json
import time
import copy
import os
import sys

from quantastica.qconvert import qobj_to_toaster
from quantastica.qiskit_toaster import (
    ToasterHttpInterface,
    ToasterCliInterface,
)

from qiskit.providers import JobV1, JobStatus, JobError
from qiskit.result import Result

logger = logging.getLogger(__name__)


# one of toaster_url or toaster_path MUST be defined
# if both are defined toaster_path takes precedence
def _run_with_qtoaster_static(
    qobj_dict,
    get_states,
    job_id,
    optimization_level=None,
    toaster_url=None,
    toaster_path=None,
):
    SEED_SIMULATOR_KEY = "seed_simulator"
    if get_states:
        shots = 1
    else:
        shots = qobj_dict["config"]["shots"]

    returns = "counts"
    if get_states:
        returns += ",state"

    seed = 0
    if SEED_SIMULATOR_KEY in qobj_dict["config"]:
        seed = qobj_dict["config"][SEED_SIMULATOR_KEY]

    converted = qobj_to_toaster(qobj_dict, {"all_experiments": False})

    dump_dir = os.getenv("TOASTER_DUMP_DIR", None)
    if dump_dir is not None:
        path_req = "%s/%s.request.json" % (dump_dir, job_id)
        with open(path_req, "w") as f:
            f.write(converted)
    if toaster_path:
        toaster = ToasterCliInterface.ToasterCliInterface(toaster_path)
    else:
        toaster = ToasterHttpInterface.ToasterHttpInterface(toaster_url)

    toasterjson = toaster.execute(
        converted.encode("utf-8"),
        job_id=job_id,
        returns=returns,
        seed=seed,
        optimization=optimization_level,
        shots=shots,
    )
    if dump_dir is not None:
        path_res = "%s/%s.response.json" % (dump_dir, job_id)
        with open(path_res, "w") as f:
            f.write(str(toasterjson))

    resultraw = None
    if toasterjson:
        resultraw = json.loads(toasterjson)

    success = resultraw is not None
    # print(success)
    data = dict()
    exp_dict = qobj_dict["experiments"][0]
    exp_header = exp_dict["header"]
    expname = exp_header["name"]
    time_taken = 0
    rawversion = "0.0.0"
    if success:
        logger.debug("Raw results from toaster:\r\n%s", resultraw)
        if isinstance(resultraw, dict):
            rawversion = resultraw.get("qtoaster_version")

        if ToasterJob._check_qtoaster_version(rawversion) is False:
            raise ValueError(
                "Unsupported qtoaster_version, got '%s' - minimum expected is '%s'.\n\rPlease update your q-toaster to latest version"
                % (rawversion, ToasterJob._MINQTOASTERVERSION)
            )
        counts = ToasterJob._convert_counts(resultraw["counts"])
        statevector = resultraw.get("statevector")
        data["counts"] = counts
        if statevector is not None and len(statevector) > 0:
            data["statevector"] = statevector
        time_taken = resultraw["time_taken"]

    result = {
        "success": success,
        "meas_level": 2,
        "shots": shots,
        "data": data,
        "header": exp_header,
        "status": "DONE",
        "time_taken": time_taken,
        "name": expname,
        "seed_simulator": seed,
        "toaster_version": rawversion,
    }
    return result


class ToasterJob(JobV1):
    DEFAULT_TOASTER_HOST = "127.0.0.1"
    DEFAULT_TOASTER_PORT = 8001
    _MINQTOASTERVERSION = "0.9.9"

    if sys.platform in ["darwin", "win32"]:
        _executor = futures.ThreadPoolExecutor(max_workers=2)
    else:
        _executor = futures.ProcessPoolExecutor(max_workers=2)
    _run_time = 0

    def __init__(
        self,
        backend,
        job_id,
        qobj,
        toaster_host,
        toaster_port,
        getstates=False,
        backend_options=None,
        use_cli=False,
    ):
        super().__init__(backend, job_id)
        self._toaster_url = "http://%s:%d" % (toaster_host, int(toaster_port))
        self._result = None
        self._qobj_dict = qobj.to_dict()
        self._futures = []
        self._getstates = getstates
        self._backend_options = backend_options
        self._use_cli = use_cli

    def submit(self):
        if len(self._futures) > 0:
            raise JobError("We have already submitted the job!")
        self._t_submit = time.time()

        logger.debug("submitting...")
        all_exps = self._qobj_dict
        exp_index = 0
        optimization_level = None
        backend_options = self._backend_options
        if backend_options:
            optimization_level = backend_options.get(
                "toaster_optimization", None
            )

        toaster_path = None
        if int(self._use_cli) != 0:
            toaster_path = "qubit-toaster"

        for exp in all_exps["experiments"]:
            exp_index += 1
            exp_job_id = "Exp_%d_%s" % (exp_index, self._job_id)
            single_exp = copy.deepcopy(all_exps)
            single_exp["experiments"] = [exp]
            self._futures.append(
                self._executor.submit(
                    _run_with_qtoaster_static,
                    single_exp,
                    self._getstates,
                    exp_job_id,
                    optimization_level=optimization_level,
                    toaster_url=self._toaster_url,
                    toaster_path=toaster_path,
                )
            )

    def wait(self, timeout=None):
        if self.status() in [JobStatus.RUNNING, JobStatus.QUEUED]:
            futures.wait(self._futures, timeout)
        if self._result is None and self.status() is JobStatus.DONE:
            results = []
            for f in self._futures:
                results.append(f.result())
            qobj_dict = self._qobj_dict
            qobjid = qobj_dict["qobj_id"]
            qobj_header = qobj_dict["header"]
            rawversion = "1.0.0"
            if len(results):
                if "toaster_version" in results[0]:
                    rawversion = results[0]["toaster_version"]

            self._result = {
                "success": True,
                "backend_name": "Toaster",
                "qobj_id": qobjid,
                "backend_version": rawversion,
                "header": qobj_header,
                "job_id": self._job_id,
                "results": results,
                "status": "COMPLETED",
            }
            ToasterJob._run_time += time.time() - self._t_submit

        if len(self._futures) > 0:
            for f in self._futures:
                if f.exception():
                    raise f.exception()

    def result(self, timeout=None):
        self.wait(timeout)
        return Result.from_dict(self._result)

    def cancel(self):
        return
        # return self._future.cancel()

    def status(self):

        if len(self._futures) == 0:
            _status = JobStatus.INITIALIZING
        else:
            running = 0
            done = 0
            canceled = 0
            error = 0
            queued = 0
            for f in self._futures:
                if f.running():
                    running += 1
                elif f.cancelled():
                    canceled += 1
                elif f.done():
                    if f.exception() is None:
                        done += 1
                    else:
                        error += 1
                else:
                    queued += 1

            if error:
                _status = JobStatus.ERROR
            elif running:
                _status = JobStatus.RUNNING
            elif canceled:
                _status = JobStatus.CANCELLED
            elif done:
                _status = JobStatus.DONE
            else:  # future is in pending state
                _status = JobStatus.QUEUED
        return _status

    def backend(self):
        """Return the instance of the backend used for this job."""
        return self._backend

    @staticmethod
    def _qtoaster_version_to_int(versionstring):
        parts = versionstring.split(".")
        verint = 0
        if len(parts) >= 3:
            verint = (
                int(parts[0]) * 1000000 + int(parts[1]) * 1000 + int(parts[2])
            )
        return verint

    @classmethod
    def _check_qtoaster_version(cls, versionstring):
        verint = cls._qtoaster_version_to_int(versionstring)
        minverint = cls._qtoaster_version_to_int(cls._MINQTOASTERVERSION)
        if verint < minverint:
            return False
        return True

    @staticmethod
    def _convert_counts(counts):
        ret = dict()
        for key in counts:
            nicekey = key.replace(" ", "")
            nicekey = hex(int(nicekey, 2))
            ret[nicekey] = counts[key]
        return ret
