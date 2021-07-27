import requests
import json
import datetime
import logging
import time
from urllib3.util.retry import Retry


def createVoltSession(token, tenantName):
    now = datetime.datetime.now()
    apiToken = "APIToken {0}".format(token)
    s = requests.Session()
    s.headers.update({'Authorization': apiToken})
    urlBase = "https://{0}.console.ves.volterra.io".format(tenantName)
    create = {
        'operation': 'createVoltSession',
        'status': 'success',
        'message': 'voltSession created',
        'time': now.strftime("%m/%d/%Y, %H:%M:%S")
    }
    session = {'session': s, 'urlBase': urlBase, 'lastOp': create}
    createCache(session)
    return session


def updateSO(s, op, status, message):
    now = datetime.datetime.now()
    action = {
        'operation': op,
        'status': status,
        'time': now.strftime("%m/%d/%Y, %H:%M:%S"),
        'message': message
    }
    s['lastOp'] = action
    return s


def createCache(s, cacheTO=60):
    urlUsers = s['urlBase'] + "/api/web/custom/namespaces/system/user_roles"
    try:
        resp = s['session'].get(urlUsers)
        resp.raise_for_status()
        users = json.loads(resp.text)['items']
    except requests.exceptions.RequestException as e:
        return updateSO(s, 'createCache', 'error', e)
    except json.decoder.JSONDecodeError as e:
        return updateSO(s, 'createCache', 'error', e)
    urlNSs = s['urlBase'] + "/api/web/namespaces"
    try:
        resp = s['session'].get(urlNSs)
        resp.raise_for_status()
        namespaces = json.loads(resp.text)['items']
    except requests.exceptions.RequestException as e:
        return updateSO(s, 'createCache', 'error', e)
    except json.decoder.JSONDecodeError as e:
        return updateSO(s, 'createCache', 'error', e)
    expiry = datetime.datetime.now() + datetime.timedelta(seconds=cacheTO)
    cache = {
        'expiry': expiry.timestamp(),
        'users': users,
        'namespaces': namespaces,
    }
    s['cache'] = cache
    updateSO(s, 'createCache', 'success', "Cache populated")


def findUserNS(email):
    userNS = ""
    if "#EXT#@" in email:
        userNS = email.split(
            '#EXT#@')[0].replace('.', '-').replace('_', '-').lower()
    else:
        userNS = email.split('@')[0].replace('.', '-').lower()
    return userNS

def cleanUserRoles(s):
    if s['cache']['expiry'] < datetime.datetime.now().timestamp():
        createCache(s)
    def_roles = [
        {'namespace': 'default', 'role': 'ves-io-default-role'},
        {'namespace': 'shared', 'role': 'ves-io-default-role'},
        {'namespace': 'system', 'role': 'ves-io-default-role'}
    ]
    cleanUsers = next(
        (user for user in s['cache']['users'] if user['namespace_roles'] == def_roles), None)
    if cleanUsers:
        for user in cleanUsers:
            delUser(user['email'], s)
    updateSO(s, 'cleanUserRoles', 'success', '{0} Users removed'.format(len(cleanUsers)))


def checkUserNS(email, s):
    if s['cache']['expiry'] < datetime.datetime.now().timestamp():
        createCache(s)
    userNS = findUserNS(email)
    thisUserNS = next(
        (ns for ns in s['cache']['namespaces'] if ns['name'] == userNS), None)
    if thisUserNS:
        return updateSO(s, 'checkUserNS', 'present', 'UserNS {0} is present'.format(userNS))
    return updateSO(s, 'checkUserNS', 'absent', 'UserNS {0} is absent'.format(userNS))


def checkUser(email, s):
    if s['cache']['expiry'] < datetime.datetime.now().timestamp():
        createCache(s)
    thisUser = next(
        (user for user in s['cache']['users'] if user['email'].lower() == email.lower()), None)
    if thisUser:
        return updateSO(s, 'checkUser', 'present', 'User {0} is present'.format(email))
    return updateSO(s, 'checkUser', 'absent', 'User {0} is absent'.format(email))


def createUserNS(email, s):
    userNS = findUserNS(email)
    url = s['urlBase'] + "/api/web/namespaces"
    nsPayload = {
        'metadata':
            {
                'annotations': {},
                'description': 'automatically generated by tenant admin',
                'disable': False,
                'labels': {},
                'name': userNS,
                'namespace': ''
            },
        'spec': {}
    }
    try:
        resp = s['session'].post(url, json=nsPayload)
        resp.raise_for_status()
        return updateSO(s, 'createUserNS', 'success', 'NS {0} was created'.format(email))
    except requests.exceptions.RequestException as e:
        return updateSO(s, 'createUserNS', 'error', e)


def delUserNS(email, s):
    userNS = findUserNS(email)
    url = s['urlBase'] + \
        "/api/web/namespaces/{0}/cascade_delete".format(userNS)
    nsPayload = {
        "name": userNS
    }
    try:
        resp = s['session'].post(url, json=nsPayload)
        resp.raise_for_status()
        return updateSO(s, 'delUserNS', 'success', 'NS {0} deleted'.format(email))
    except requests.exceptions.RequestException as e:
        return updateSO(s, 'delUserNS', 'error', e)


def createUserRoles(email, first_name, last_name, s, createdNS=None, exists=False, admin=False):
    url = s['urlBase'] + "/api/web/custom/namespaces/system/user_roles"
    if admin:
        namespace_roles = [
            {'namespace': 'system', 'role': 'ves-io-admin-role'},
            {'namespace': '*', 'role': 'ves-io-admin-role'},
            {'namespace': 'default', 'role': 'ves-io-admin-role'},
            {'namespace': 'shared', 'role': 'ves-io-admin-role'}
        ]
    else:
        namespace_roles = [
            {'namespace': 'system', 'role': 'ves-io-power-developer-role'},
            {'namespace': 'system', 'role': 'f5-demo-infra-write'},
            {'namespace': '*', 'role': 'ves-io-monitor-role'},
            {'namespace': 'default', 'role': 'ves-io-power-developer-role'},
            {'namespace': 'shared', 'role': 'ves-io-power-developer-role'}
        ]
    userPayload = {
        'email': email.lower(),
        'first_name': first_name,
        'last_name': last_name,
        'name': email.lower(),
        'idm_type': 'SSO',
        'namespace': 'system',
        'namespace_roles': namespace_roles,
        'type': 'USER'
    }
    if createdNS:
        userPayload['namespace_roles'].append(
            {'namespace': createdNS, 'role': 'ves-io-admin-role'})
    try:
        if exists:
            resp = s['session'].put(url, json=userPayload)
        else:
            resp = s['session'].post(url, json=userPayload)
        resp.raise_for_status()
        return updateSO(s, 'createUserRoles', 'success', 'User {0} and Roles created/updated'.format(email))
    except requests.exceptions.RequestException as e:
        return updateSO(s, 'createUserRoles', 'error', e)


def delUser(email, s):
    url = s['urlBase'] + "/api/web/custom/namespaces/system/users/cascade_delete"
    userPayload = {
        "email": email.lower(),
        "namespace": "system"
    }
    try:
        resp = s['session'].post(url, json=userPayload)
        resp.raise_for_status()
        return updateSO(s, 'delUser', 'success', 'User {0} deleted'.format(email))
    except requests.exceptions.RequestException as e:
        return updateSO(s, 'delUser', 'error', e)


def cliAdd(s, email, first_name, last_name, createNS, overwrite, admin):
    createdNS = None
    userExist = False
    nsExist = False
    checkUser(email, s)
    if s['lastOp']['status'] == 'present':
        userExist = True
    checkUserNS(email, s)
    if s['lastOp']['status'] == 'present':
        nsExist = True
    if overwrite:
        if createNS:
            if nsExist:
                delUserNS(email, s)
            createUserNS(email, s)
            createdNS = findUserNS(email)
        createUserRoles(email, first_name, last_name,
                        s, createdNS, userExist, admin)
        if s['lastOp']['status'] == 'success':
            return {'status': 'success'}
        else:
            return {'status': 'failure', 'reason': 'User creation failed', 'log': s['lastOp']}
    else:
        if nsExist or userExist:
            return {'status': 'failure', 'reason': 'NS or User already exists', 'log': s['lastOp']}
        if createNS:
            createUserNS(email, s)
            createdNS = findUserNS(email)
        createUserRoles(email, first_name, last_name,
                        s, createdNS, False, admin)
        if s['lastOp']['status'] == 'success':
            return {'status': 'success'}
        else:
            return {'status': 'failure', 'reason': 'User creation failed', 'log': s['lastOp']}


def cliRemove(s, email):
    userExist = False
    nsExist = False
    checkUser(email, s)
    if s['lastOp']['status'] == 'present':
        userExist = True
    checkUserNS(email, s)
    if s['lastOp']['status'] == 'present':
        nsExist = True
    if not nsExist and not userExist:
        return {'status': 'failure', 'reason': 'Neither NS nor User exist', 'log': s['lastOp']}
    if nsExist:
        delUserNS(email, s)
        if s['lastOp']['status'] != 'success':
            return {'status': 'failure', 'reason': 'NS deletion failed', 'log': s['lastOp']}
    if userExist:
        delUser(email, s)
        if s['lastOp']['status'] != 'success':
            return {'status': 'failure', 'reason': 'User deletion failed', 'log': s['lastOp']}
    return {'status': 'success'}


def isWingmanReady(count=0):
    try:
        r = requests.get("http://localhost:8070/status")
        if r.status_code == 200 and r.text == "READY":
            logging.debug("wingman ready")
            return True
        else:
            logging.debug("wingman not ready")
            if count == 3:
                return False
            else:
                time.sleep(10)
                return isWingmanReady(count+1)
    except requests.ConnectionError:
        time.sleep(10)
        return isWingmanReady(count+1)


def getWingmanSecret(blindfoldText):
    payload = {
        "type": "blindfold",
        "location": f"string:///{blindfoldText}"
    }

    logging.debug(payload)

    r = requests.post("http://localhost:8070/secret/unseal", data=payload)

    if r.status_code == 200:
        return r.text
    else:
        return None
