import datetime
import logging
import os

from volterra_helpers import createVoltSession, updateToken

import azure.functions as func


def main(updateTimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if updateTimer.past_due:
        logging.info('Token Update is due to run.')

    logging.info('Token Update ran at %s', utc_timestamp)

    required_vars = {
        'VoltTenantName': False,
        'VoltTenantApiToken': False,
        'VoltTenantTokenName': False
    }
    for v in required_vars:
        required_vars[v] = os.environ.get(v, False)

        if required_vars[v] == False:
            raise ValueError("A value must be provided for {0}".format(v))

    s = createVoltSession(
        required_vars['VoltTenantApiToken'], required_vars['VoltTenantName'])
    logging.info(s['lastOp'])

    updateToken(s, required_vars['VoltTenantTokenName'], 7)
    logging.info(s['lastOp'])