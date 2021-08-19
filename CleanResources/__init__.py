import datetime
import logging
import os

from volterra_helpers import createVoltSession
from clean_helpers import getStaleSites, getStaleUserNSs

import azure.functions as func


def main(cleanTimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if cleanTimer.past_due:
        logging.info('Clean Resources is due to run.')

    logging.info('Clean Resources ran at %s', utc_timestamp)

    required_vars = {
        'VoltTenantName': False,
        'VoltTenantApiToken': False
    }
    for v in required_vars:
        required_vars[v] = os.environ.get(v, False)

        if required_vars[v] == False:
            raise ValueError("A value must be provided for {0}".format(v))

    s = createVoltSession(
        required_vars['VoltTenantApiToken'], required_vars['VoltTenantName'])
    logging.info(s['lastOp'])

    sites = getStaleSites(s, 30)
    logging.info(s['lastOp'])

    ns = getStaleUserNSs(s, 30)
    logging.info(s['lastOp'])

    logging.info("DEBUG sites: {}".format(sites))
    logging.info("DEBUG NSs: {}".format(ns))