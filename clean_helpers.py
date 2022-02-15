import requests
import logging
import datetime
from dateutil.parser import *

from volterra_helpers import updateSO, findUserNS, createUserNS, delUserNS

def findExpiry(staleDays: int):
    expiry = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=staleDays)
    return expiry

def getStaleSites(s: dict, staleDays: int = 30):
    url = s['urlBase'] + "/api/config/namespaces/system/sites?report_fields"
    try:
        resp = s['session'].get(url)
        resp.raise_for_status()
        staleSites = []
        expiry = findExpiry(staleDays)
        for item in resp.json()['items']:
            #Check for FAILED sites last modified before expiry
            if (item['get_spec']['site_type'] == 'CUSTOMER_EDGE') and \
                (item['get_spec']['site_state'] == 'FAILED') and \
                (parse(item['system_metadata']['modification_timestamp']) < expiry):
                staleSites.append(item['name'])
            #Check for WAITING_FOR_REGISTRATION created before expiry
            if (item['get_spec']['site_type'] == 'CUSTOMER_EDGE') and \
                (item['get_spec']['site_state'] == 'WAITING_FOR_REGISTRATION') and \
                (parse(item['system_metadata']['creation_timestamp']) < expiry):
                staleSites.append(item['name'])
        updateSO(s, 'getStaleSites', 'success', 'fetched stale sites')
        return staleSites
    except requests.exceptions.RequestException as e:
        updateSO(s, 'getStaleSites', 'error', e)
        return None

def getStaleSitesv2(s: dict, staleDays: int = 30):
    url = s['urlBase'] + "/api/config/namespaces/system/sites?report_fields"
    try:
        resp = s['session'].get(url)
        resp.raise_for_status()
        staleSites = []
        expiry = findExpiry(staleDays)
        for item in resp.json()['items']:
            #Check for FAILED sites last modified before expiry
            if (item['get_spec']['site_type'] == 'CUSTOMER_EDGE') and \
                (item['get_spec']['site_state'] == 'FAILED') and \
                (parse(item['system_metadata']['modification_timestamp']) < expiry):
                staleSites.append(item['name'])
            #Check for WAITING_FOR_REGISTRATION created before expiry
            if (item['get_spec']['site_type'] == 'CUSTOMER_EDGE') and \
                (item['get_spec']['site_state'] == 'WAITING_FOR_REGISTRATION') and \
                (parse(item['system_metadata']['creation_timestamp']) < expiry):
                staleSites.append({ "name": item['name'], "kind": item['owner_view']['kind'] })
        updateSO(s, 'getStaleSites', 'success', 'fetched stale sites')
        return staleSites
    except requests.exceptions.RequestException as e:
        updateSO(s, 'getStaleSites', 'error', e)
        return None

def getStaleUsers(s: dict, staleDays: int = 60):
    url = s['urlBase'] + "/api/web/custom/namespaces/system/user_roles"
    try:
        resp = s['session'].get(url)
        resp.raise_for_status()
        staleUserNSs = []
        for item in resp.json()['items']:
            if (item['last_login_timestamp'] is None) or (parse(item['last_login_timestamp']) < findExpiry(staleDays)):
                staleUserNSs.append(findUserNS(item['email'])) 
        updateSO(s, 'getStaleUserNSs', 'success', 'fetched stale user namespaces')
        return staleUserNSs
    except requests.exceptions.RequestException as e:
        updateSO(s, 'getStaleUserNSs', 'error', e)
        return None

def decomSites(sites: list, s: dict) -> dict:
    decommedSites = []
    errors = []
    for site in sites:
        url = s['urlBase'] + "/api/register/namespaces/system/site/{0}/state".format(site)
        sitePayload = {
            "name": site,
            "namespace": "system",
            "state": "DECOMISSIONING"
        }
        try:
            resp = s['session'].post(url, json=sitePayload)
            resp.raise_for_status()
            decommedSites.append(site)
        except requests.exceptions.RequestException as e:
            errors.append(e)
    if len(errors) > 0:
        return updateSO(s, 'decomSites', 'error', 'Decommed: {0}\nErrors: {1}'.format(decommedSites, errors))
    else:
        return updateSO(s, 'decomSites', 'success', 'Decommed: {0}'.format(decommedSites))

def cleanStaleUserNSs(s: dict, users: list, staleDays: int = 60):
    if len(users) > 0:
        cleanedNSs = []
        noop = []
        for user in users:
            url = s['urlBase'] + "/api/web/namespaces/{}".format(findUserNS(user))
            try:
                r = s['session'].get(url)
                if r.status_code == 200:
                    if parse(r.json()['system_metadata']['creation_timestamp']) < findExpiry(staleDays):
                        delUserNS(user, s)
                        desc = 'cleaned by tenant admin at {0}'.format(datetime.datetime.now().isoformat())
                        createUserNS(user, s, desc)
                        cleanedNSs.append(user)
                    else:
                        noop.append(user)
                else:
                    noop.append(user)
            except requests.exceptions.RequestException as e:
                logging.error("Failed to delete user {}".format(user))
        return updateSO(s, 'cleanStaleUserNSs', 'success', 'Cleaned NSs: {0}, NoOp users:{1}'.format(cleanedNSs, noop))
    else:
        return updateSO(s, 'cleanStaleUserNSs', 'success', 'no stale NSs to clean')
