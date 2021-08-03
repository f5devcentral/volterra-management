import datetime
import logging
import os

from volterra_helpers import createVoltSession, cleanUserRoles

import azure.functions as func


def main(cleanTimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if cleanTimer.past_due:
        logging.info('Tenant User Clean is due to run.')

    logging.info('Tenant User Clean ran at %s', utc_timestamp)

    required_vars = {'VoltTenantName': False,
                    'VoltTenantApiToken': False}

    for v in required_vars:
        required_vars[v] = os.environ.get(v, False)

        if required_vars[v] == False:
            raise ValueError("A value must be provided for {0}".format(v))

    s = createVoltSession(
        required_vars['VoltTenantApiToken'], required_vars['VoltTenantName'])
    logging.info(s['lastOp'])

    cleanUserRoles(s)
    logging.info(s['lastOp'])