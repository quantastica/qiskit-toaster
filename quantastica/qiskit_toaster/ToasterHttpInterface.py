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
import urllib
from urllib import request
import time
import socket


logger = logging.getLogger(__name__)


class ToasterHttpInterface:
    def __init__(self, toaster_url):
        self.toaster_url = toaster_url

    def execute(
        self,
        jsonstr,
        job_id=None,
        seed=None,
        shots=None,
        returns=None,
        optimization=None,
    ):

        params = dict()
        params["x-qtc-return"] = returns or "counts"
        params["x-qtc-shots"] = "%d" % (shots or 1)
        params["x-qtc-jobid"] = job_id or ""
        if seed:
            params["x-qtc-seed"] = "%d" % seed
        if optimization:
            params["x-qtc-optimization"] = "%d" % optimization

        logger.info("Sending circuit to toaster, url: %s", self.toaster_url)
        logger.info("Simulation params: %s", params)
        timeout = None
        params["content-type"] = "application/json"
        req = request.Request(
            self.toaster_url + "/submit", data=jsonstr, headers=params
        )
        txt = None
        max_retries = 5
        retry_count = 0

        while True:
            try:
                response = request.urlopen(req, timeout=timeout)
            except socket.timeout as e:
                logger.debug("Exception raised: %s", e)
                txt = self._fetch_last_response(timeout, job_id)
                if txt is None:
                    continue
                else:
                    break
            except urllib.error.HTTPError as e:
                logger.debug("Exception raised: %s", e)
                # already submitted, lets fetch results
                if e.code == 409:
                    txt = self._fetch_last_response(timeout, job_id)
                    if txt is None:
                        continue
                    else:
                        break
                else:
                    raise RuntimeError(
                        "Error received from API(2): %s" % str(e)
                    )
            except Exception:
                if retry_count < max_retries:
                    retry_count += 1
                    logger.debug(
                        "Connection failed, retrying (#%d)...", retry_count
                    )
                    time.sleep(0.2)
                else:
                    msg = (
                        "Failed to connect to qubit-toaster, probably not running (url: %s)"
                        % self.toaster_url
                    )
                    logger.critical(msg)
                    raise RuntimeError(msg)
            else:
                txt = response.read().decode("utf8")
                break

        return txt

    def _fetch_last_response(self, timeout, job_id):
        req = request.Request("%s/pollresult/%s" % (self.toaster_url, job_id))
        txt = None
        while True:
            try:
                response = request.urlopen(req, timeout=timeout)
            except urllib.error.HTTPError as e:
                raise RuntimeError("Error received from API(1): %s" % str(e))
            except (socket.timeout, urllib.error.URLError) as e:
                logger.debug("Exception raised: %s", e)
                time.sleep(0.2)
                continue
            else:
                txt = response.read().decode("utf8")
                break

        return txt
