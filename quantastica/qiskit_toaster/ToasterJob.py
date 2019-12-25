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
import functools
import os
import time
import subprocess
import json
import tempfile
import requests

from quantastica.qconvert import qobj_to_toaster

from qiskit.providers import BaseJob, JobStatus, JobError
from qiskit.qobj import validate_qobj_against_schema
from qiskit.result import Result

logger = logging.getLogger(__name__)


class ToasterJob(BaseJob):
    _MINQTOASTERVERSION = '0.9.7'
    
    if sys.platform in ['darwin', 'win32']:
        _executor = futures.ThreadPoolExecutor()
    else:
        _executor = futures.ProcessPoolExecutor()

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

        logger.debug("submit...")
        validate_qobj_against_schema(self._qobj)
        self._future = self._executor.submit(self._run_with_qtoaster)

    def wait(self, timeout=None):
        if self.status() is JobStatus.RUNNING :
            futures.wait([self._future], timeout);
            if self._future.exception() :
                raise self._future.exception()

    def result(self, timeout=None):
        self.wait(timeout)
        return Result.from_dict(self._result);

    def cancel(self):
        return
        # return self._future.cancel()

    def status(self):

        if self._future is None:
            _status = JobStatus.INITIALIZING
        elif self._future.running():
            _status = JobStatus.RUNNING
        elif self._future.cancelled():
            _status = JobStatus.CANCELLED
        elif self._future.done():
            _status = JobStatus.DONE if self._future.exception() is None else JobStatus.ERROR
        else:
            _status = JobStatus.INITIALIZING

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
            ret[nicekey] = counts[key];
        return ret

    @staticmethod
    def _convert_qobj(qobj, destinationfn):
        if os.path.exists(destinationfn):
            os.remove(destinationfn)

        converted = qobj_to_toaster(qobj, { "all_experiments": False })

        with open(destinationfn, "w") as outfile:
            json.dump(converted, outfile)

    def _run_with_qtoaster(self):
        tmpjsonfilename = tempfile.mktemp()
        qobj_dict = self._qobj.to_dict()
        shots = qobj_dict['config']['shots']
        self._convert_qobj(qobj_dict, tmpjsonfilename)

        args = [
            self._toasterpath,
            tmpjsonfilename,
            "-r",
            "measure_all",
            "%d"%shots
        ]
        if self._getstates:
            args.append("-r")
            args.append("state")

        logger.info("Running q-toaster with following params:")
        logger.info(args)
        proc = subprocess.run(args, stdout=subprocess.PIPE)
        os.remove(tmpjsonfilename)
        qtoasterjson = proc.stdout

        resultraw = json.loads(qtoasterjson)
        logger.debug("Raw results from toaster:\r\n%s",resultraw)

        if isinstance(resultraw , dict) :
            rawversion = resultraw.get('qtoaster_version')
        else:
            rawversion = "0.0.0"

        if ToasterJob._check_qtoaster_version(rawversion) == False :
            raise ValueError(
                "Unsupported qtoaster_version, got '%s' - minimum expected is '%s'.\n\rPlease update your q-toaster to latest version"%(rawversion,self._MINQTOASTERVERSION))

        counts = self._convert_counts(resultraw['counts'])

        qobjid = qobj_dict['qobj_id']
        qobj_header = qobj_dict['header']
        exp_dict = qobj_dict['experiments'][0]
        exp_header = exp_dict['header']
        expname = exp_header['name']
        qubit_count = exp_dict['config']['n_qubits']
        statevector = resultraw.get('statevector')
        data = dict()
        data['counts'] = counts;
        if statevector is not None and len(statevector) > 0:
            data['statevector'] = statevector

        self._result = {
            'success': True, 
            'backend_name': qobj_header['backend_name'], 
            'qobj_id': qobjid ,
            'backend_version': rawversion, 
            'header': qobj_header,
            'job_id': self._job_id, 
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
