import datetime
import logging
import os

from volterra_helpers import createVoltSession
from quota_helpers import getQuota, getQuotaViolations, postQuotaViolations

import azure.functions as func


def main(quotaTimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if quotaTimer.past_due:
        logging.info('Quota Alert is due to run.')

    logging.info('Quota Alert ran at %s', utc_timestamp)

    required_vars = {
        'VoltTenantName': False,
        'VoltTenantApiToken': False,
        'TeamsWebhookUrl': False
    }

    for v in required_vars:
        required_vars[v] = os.environ.get(v, False)

        if required_vars[v] == False:
            raise ValueError("A value must be provided for {0}".format(v))

    s = createVoltSession(
        required_vars['VoltTenantApiToken'], required_vars['VoltTenantName'])
    logging.info(s['lastOp'])

    quotas = getQuota("system", s)
    logging.info(s,['lastOp'])

    quotaViolations = getQuotaViolations(quotas)

    if len(quotaViolations) > 0:
        logging.info(
            "The following quota objects are above the desired threshold:")
        for q in quotaViolations:
            logging.info(q)
        # post to teams channel
        webhookUrl = os.environ.get('TeamsWebhookUrl', False)
        if(webhookUrl):
            postQuotaViolations(webhookUrl, quotaViolations,
                                required_vars['VoltTenantName'])

    else:
        logging.info("No quota issues found")