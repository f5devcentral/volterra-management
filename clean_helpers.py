import requests
import logging
import datetime
from dateutil.parser import *

from volterra_helpers import updateSO, findUserNS

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

def getStaleUserNSs(s: dict, staleDays: int = 30):
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

def cleanStaleSites(s: dict, sites: list):
    for site in sites:
        url = s['urlBase'] + "/api/web/namespaces/system/renew/api_credentials/{}".format(cluster)
        try:
            r = requests.delete(url)
            if r.status_code != 200:
                logging.error("Failed to delete cluster {}".format(cluster))
        except exceptions.ConnectionError:
            logging.error("Failed to delete cluster {}".format(cluster)) 

def GetUsers(s: dict):
    url = s['urlBase'] + "/api/web/namespaces/system/users"
    return None

def findStaleUsers(staleDays: int = 30, users: list = None):
    url = "https://volterra-api.herokuapp.com/api/web/namespaces/system/users"
    try:
        r = requests.get(url)
        if r.status_code != 200:
            logging.error("Failed to get users")
            return None
        else:
            return r.json()
    except exceptions.ConnectionError:
        logging.error("Failed to get users")
        return None

def CleanStaleUsers(s: dict, users: list):
    if len(users) > 0:
        for user in users:
            url = s['urlBase'] + "/api/web/namespaces/system/users/{}".format(user)
            try:
                r = requests.delete(url)
                if r.status_code != 200:
                    logging.error("Failed to delete user {}".format(user))
            except exceptions.ConnectionError:
                logging.error("Failed to delete user {}".format(user))
    else:
        return updateSO(s, 'CleanStaleUsers', 'success', 'no stale users')
