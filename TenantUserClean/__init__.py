import datetime
import logging
import os

from volterra_helpers import createVoltSession, cleanUserRoles

import azure.functions as func


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)

    required_vars = {'VoltTenantName': False,
                    'VoltTenantApiToken': False}

    for v in required_vars:
        required_vars[v] = os.environ.get(v, False)

        if required_vars[v] == False:
            raise ValueError("A value must be provided for {0}".format(v))

    s = createVoltSession(
        required_vars['VoltTenantApiToken'], required_vars['VoltTenantName'])

    cleanUserRoles(s)
    logging.info(s['lastOp'])