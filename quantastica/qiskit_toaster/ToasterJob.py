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
import sys
import subprocess
import json
import time

from quantastica.qconvert import qobj_to_toaster

from qiskit.providers import BaseJob, JobStatus, JobError
from qiskit.qobj import validate_qobj_against_schema
from qiskit.result import Result

logger = logging.getLogger(__name__)

def _run_with_qtoaster_static(qobj_dict, get_states, toaster_path, job_id):
    ToasterJob._execution_count += 1
    _t_start = time.time()
    SEED_SIMULATOR_KEY = "seed_simulator"
    if get_states :
        shots = 1
    else:
        shots = qobj_dict['config']['shots']
    _t_before_convert = time.time()
    # print(json.dumps(qobj_dict))
    converted = qobj_to_toaster(qobj_dict, { "all_experiments": False })
    _t_after_convert = time.time()
    ToasterJob._qconvert_time += _t_after_convert - _t_before_convert
    args = [
        toaster_path,
        "-",
        "-r",
        "counts",
        "-s",
        "%d"%shots
    ]
    if get_states:
        args.append("-r")
        args.append("state")
    if SEED_SIMULATOR_KEY in qobj_dict['config']:
        args.append("--seed")
        args.append("%d"%qobj_dict['config'][SEED_SIMULATOR_KEY])
    logger.info("Running q-toaster with following params:")
    logger.info(args)
    proc = subprocess.run(
        args, 
        input=converted.encode(),
        stdout=subprocess.PIPE )

    qtoasterjson = proc.stdout

    resultraw = json.loads(qtoasterjson)
    logger.debug("Raw results from toaster:\r\n%s",resultraw)
    if isinstance(resultraw , dict) :
        rawversion = resultraw.get('qtoaster_version')
    else:
        rawversion = "0.0.0"
    ToasterJob._qtoaster_time += time.time() - _t_after_convert

    if ToasterJob._check_qtoaster_version(rawversion) == False :
        raise ValueError(
            "Unsupported qtoaster_version, got '%s' - minimum expected is '%s'.\n\rPlease update your q-toaster to latest version"%(rawversion,self._MINQTOASTERVERSION))

    counts = ToasterJob._convert_counts(resultraw['counts'])
    qobjid = qobj_dict['qobj_id']
    qobj_header = qobj_dict['header']
    exp_dict = qobj_dict['experiments'][0]
    exp_header = exp_dict['header']
    expname = exp_header['name']
    statevector = resultraw.get('statevector')
    data = dict()
    data['counts'] = counts;
    if statevector is not None and len(statevector) > 0:
        data['statevector'] = statevector

    backend_name = "Backend name"

    result = {
        'success': True, 
        'backend_name': backend_name, 
        'qobj_id': qobjid ,
        'backend_version': rawversion, 
        'header': qobj_header,
        'job_id': job_id, 
        'results': [
            {
                'success': True, 
                'meas_level': 2, 
                'shots': shots, 
                'data': data, 
                'header': exp_header, 
                'status': 'DONE', 
                'time_taken': resultraw['time_taken'], 
                'name': expname, 
                'seed_simulator': 0
            }
            ], 
        'status': 'COMPLETED'
    }
    return result

class ToasterJob(BaseJob):
    _MINQTOASTERVERSION = '0.9.9'
    
    _executor = futures.ProcessPoolExecutor()
    _qconvert_time = 0
    _qtoaster_time = 0
    _run_time = 0
    _execution_count = 0

    def __init__(self, backend, job_id, qobj, toasterpath, 
                 getstates = False):
        super().__init__(backend, job_id)
        self._result = None
        self._qobj = qobj
        self._future = None
        self._toasterpath = toasterpath;
        self._getstates = getstates

    def submit(self):
        if self._future is not None:
            raise JobError("We have already submitted the job!")
        self._t_submit = time.time()

        logger.debug("submitting...")
        print("Exp count:",len(self._qobj.to_dict()["experiments"]))
        self._future = self._executor.submit(_run_with_qtoaster_static,
            self._qobj.to_dict(),
            self._getstates,
            self._toasterpath,
            self._job_id
            )

    def wait(self, timeout=None):
        if self.status() in [JobStatus.RUNNING, JobStatus.QUEUED] :
            futures.wait([self._future], timeout)
        if not self._result and self.status() is JobStatus.DONE :
            self._result = self._future.result()
            ToasterJob._run_time += time.time() - self._t_submit

        if self._future is not None:
            if self._future.exception() :
                raise self._future.exception()

    def result(self, timeout=None):
        self.wait(timeout)
        return Result.from_dict(self._result)

    def cancel(self):
        return
        #return self._future.cancel()

    def status(self):

        if self._future is None:
            _status = JobStatus.INITIALIZING
        elif self._future.running():
            _status = JobStatus.RUNNING
        elif self._future.cancelled():
            _status = JobStatus.CANCELLED
        elif self._future.done():
            _status = JobStatus.DONE if self._future.exception() is None else JobStatus.ERROR
        else: # future is in pending state
            _status = JobStatus.QUEUED
        return _status

    def backend(self):
        """Return the instance of the backend used for this job."""
        return self._backend
    
    @staticmethod
    def _qtoaster_version_to_int(versionstring):
        parts = versionstring.split(".")
        verint = 0
        if len(parts) >= 3 :
            verint = int(parts[0])*1000000 + int(parts[1])*1000 + int(parts[2])
        return verint

    @classmethod
    def _check_qtoaster_version(cls, versionstring):
        verint = cls._qtoaster_version_to_int(versionstring)
        minverint = cls._qtoaster_version_to_int(cls._MINQTOASTERVERSION)
        if verint < minverint :
            return False
        return True

    @staticmethod
    def _convert_counts(counts):
        ret = dict()
        for key in counts:
            nicekey = key.replace(' ','')
            nicekey = hex(int(nicekey,2))
            ret[nicekey] = counts[key]
        return ret


