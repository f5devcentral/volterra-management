import requests
import logging
import datetime

from volterra_helpers import updateSO

def getStaleSites(s: dict, staleDays: int = 30):
    url = s['urlBase'] + "/api/config/namespaces/system/sites"
    try:
        resp = s['session'].get(url)
        resp.raise_for_status()
        expiry = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=staleDays)
        staleSites = []
        for item in resp.json()['items']:
            if (item['get_spec']['site_type'] == 'CUSTOMER_EDGE') and \
            (item['get_spec']['site_state'] == 'FAILED') and \
            (datetime.datetime.fromisoformat(item['system_metadata']['modification_timestamp'].replace('Z', '+00:00')) < expiry):
                staleSites.append(item['name'])
        logging.info("DEBUG (stale sites): {0}".format(staleSites))
        if len(staleSites) > 0:
            updateSO(s, 'getStaleSites', 'success', 'fetched stale sites')
            return staleSites
        else:
            updateSO(s, 'getStaleSites', 'success', 'No stale sites found')
            return None
    except requests.exceptions.RequestException as e:
        updateSO(s, 'getStaleSites', 'error', e)
        return None

def cleanStaleSites(s: dict, clusters: list):
    for cluster in clusters:
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
