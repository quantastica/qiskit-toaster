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
import subprocess
import json
import time
import copy

from quantastica.qconvert import qobj_to_toaster

from qiskit.providers import BaseJob, JobStatus, JobError
from qiskit.result import Result

logger = logging.getLogger(__name__)

def _run_with_qtoaster_static(qobj_dict, get_states, toaster_path, job_id):
    SEED_SIMULATOR_KEY = "seed_simulator"
    if get_states :
        shots = 1
    else:
        shots = qobj_dict['config']['shots']
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
    seed = 0
    if SEED_SIMULATOR_KEY in qobj_dict['config']:
        seed = qobj_dict['config'][SEED_SIMULATOR_KEY]
        args.append("--seed")
        args.append("%d"%seed)
    logger.info(args)
    proc = subprocess.Popen(
        args,
        close_fds = False,
        restore_signals = False,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE )

    converted = qobj_to_toaster(qobj_dict, { "all_experiments": False })

    logger.info("Running q-toaster with following params:")
    proc.stdin.write(converted.encode())
    proc.stdin.close()
    proc.wait()
    qtoasterjson = proc.stdout.read()
    proc.stdout.close()
    resultraw = json.loads(qtoasterjson)
    logger.debug("Raw results from toaster:\r\n%s",resultraw)
    if isinstance(resultraw , dict) :
        rawversion = resultraw.get('qtoaster_version')
    else:
        rawversion = "0.0.0"

    if ToasterJob._check_qtoaster_version(rawversion) == False :
        raise ValueError(
            "Unsupported qtoaster_version, got '%s' - minimum expected is '%s'.\n\rPlease update your q-toaster to latest version"%(rawversion,ToasterJob._MINQTOASTERVERSION))

    counts = ToasterJob._convert_counts(resultraw['counts'])
    exp_dict = qobj_dict['experiments'][0]
    exp_header = exp_dict['header']
    expname = exp_header['name']
    statevector = resultraw.get('statevector')
    data = dict()
    data['counts'] = counts;
    if statevector is not None and len(statevector) > 0:
        data['statevector'] = statevector

    result = {
                'success': True,
                'meas_level': 2,
                'shots': shots,
                'data': data,
                'header': exp_header,
                'status': 'DONE',
                'time_taken': resultraw['time_taken'],
                'name': expname,
                'seed_simulator': seed,
                'toaster_version' : rawversion
            }
    return result

class ToasterJob(BaseJob):
    _MINQTOASTERVERSION = '0.9.9'

    _executor = futures.ProcessPoolExecutor()
    _run_time = 0

    def __init__(self, backend, job_id, qobj, toasterpath,
                 getstates = False):
        super().__init__(backend, job_id)
        self._result = None
        self._qobj_dict = qobj.to_dict()
        self._futures = []
        self._toasterpath = toasterpath
        self._getstates = getstates

    def submit(self):
        if len(self._futures)>0:
            raise JobError("We have already submitted the job!")
        self._t_submit = time.time()

        logger.debug("submitting...")
        all_exps = self._qobj_dict
        for exp in all_exps["experiments"]:
            single_exp = copy.deepcopy(all_exps)
            single_exp["experiments"]=[exp]
            self._futures.append(self._executor.submit(_run_with_qtoaster_static,
                single_exp,
                self._getstates,
                self._toasterpath,
                self._job_id)
                )

    def wait(self, timeout=None):
        if self.status() in [JobStatus.RUNNING, JobStatus.QUEUED] :
            futures.wait(self._futures, timeout)
        if self._result is None and self.status() is JobStatus.DONE :
            results = []
            for f in self._futures:
                results.append(f.result())
            qobj_dict = self._qobj_dict
            qobjid = qobj_dict['qobj_id']
            qobj_header = qobj_dict['header']
            rawversion = "1.0.0"
            if len(results):
                if "toaster_version" in results[0]:
                    rawversion = results[0]['toaster_version']

            self._result = {
                'success': True,
                'backend_name': "Toaster",
                'qobj_id': qobjid ,
                'backend_version': rawversion,
                'header': qobj_header,
                'job_id': self._job_id,
                'results': results,
                'status': 'COMPLETED'
            }
            ToasterJob._run_time += time.time() - self._t_submit

        if len(self._futures)>0:
            for f in self._futures:
                if f.exception() :
                    raise f.exception()

    def result(self, timeout=None):
        self.wait(timeout)
        return Result.from_dict(self._result)

    def cancel(self):
        return
        #return self._future.cancel()

    def status(self):

        if len(self._futures)==0 :
            _status = JobStatus.INITIALIZING
        else :
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

            if error :
                _status = JobStatus.ERROR
            elif running :
                _status = JobStatus.RUNNING
            elif canceled :
                _status = JobStatus.CANCELLED
            elif done :
                _status = JobStatus.DONE
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
