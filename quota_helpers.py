import requests
import logging

from volterra_helpers import updateSO
from requests import exceptions

def getQuota(namespace="system", s=None):
    url = s['urlBase'] + \
        "/api/web/namespaces/{0}/quota/usage".format(namespace)
    resp = s['session'].get(url)
    resp.raise_for_status()
    updateSO(s, 'getQuota', 'success', "Quotas retrieved")
    return resp.json()

def getQuotaViolations(quotas=None):
    quotaViolations = []
    for key in quotas['quota_usage']:
        logging.debug("Processing {0} quota:".format(key))
        if not quota_within_threshold(quotas['quota_usage'][key]):
            quotaViolations.append(key)
    return quotaViolations

def quota_within_threshold(q=None, t=.9):
    limit = q['limit']['maximum']
    usage = q['usage']['current']
    logging.debug("limit: {0}, usage: {1}".format(limit, usage))
    # check if there are set limits on the quota
    # we don't worry about limits less than 0 or equal to 1
    if limit < 2:
        return True
    elif usage > (limit * t):
        return False
    else:
        return True

def postQuotaViolations(url, quotaViolations, tenant):
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "0076D7",
        "summary": "Quota Threshold Warning",
        "sections": [{
            "activityTitle": "Quota Threshold Warning",
            "activitySubtitle": "on {0} tenant".format(tenant),
            "activityImage": "https://teamsnodesample.azurewebsites.net/static/img/image9.png",
            "facts": [{
                "name": "Objects above threshold:",
                "value": "{0}".format(', '.join(quotaViolations))
            }],
            "markdown": "true"
        }]
    }

    logging.debug(payload)
    logging.debug(url)

    resp = requests.post(url, json=payload)

    logging.debug(resp.status_code)
    logging.debug(resp.text)
