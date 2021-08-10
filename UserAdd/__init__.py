import datetime
import logging
import os

from AAD_helpers import retrieveAccessToken, voltUsers2Add, voltUsers2Remove
from ms_graph import getUser
from volterra_helpers import createVoltSession, updateSO, addUser, removeUserRoles

import azure.functions as func


def main(addTimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if addTimer.past_due:
        logging.info('User Add is due to run.')

    logging.info('User Add ran at %s', utc_timestamp)

    required_vars = {
        'AADclientID': False,
        'AADtenantID': False,
        'AADsecret': False,
        'AADGroupName': False,
        'VoltTenantApiToken': False,
        'VoltTenantName': False
    }
    for v in required_vars:
        required_vars[v] = os.environ.get(v, False)

        if required_vars[v] == False:
            raise ValueError("A value must be provided for {0}".format(v))

    # Get VoltConsole Session
    s = createVoltSession(required_vars['VoltTenantApiToken'], required_vars['VoltTenantName'])
    logging.info(s['lastOp'])

    # Clean VoltConsole Users
    removeUserRoles(s)
    logging.info(s['lastOp'])

    # Add Users from AAD
    AADtoken = retrieveAccessToken(required_vars['AADclientID'], required_vars['AADtenantID'], required_vars['AADsecret'])
    addUsers: list[type[dict]] = voltUsers2Add(s, AADtoken, required_vars['AADGroupName'])
    for user in addUsers:
        email = user['userPrincipalName']
        thisUser = getUser(AADtoken, email)
        addUser(s, email, thisUser['givenName'], thisUser['surname'])
        logging.info(s['lastOp'])

    # Log Users to Remove (Information only)
    cleanUsers: list[type[dict]] = voltUsers2Remove(s, AADtoken, required_vars['AADGroupName'])
    ## This is not necessary once the 'testuser' without an email is removed
    if len(cleanUsers[0]['userPrincipalName']) > 0:
        remUsers = []
        for user in cleanUsers:
            if len(user['userPrincipalName']) > 0:
                remUsers.append(user['userPrincipalName'])
        updateSO(s, 'cleanUsers', 'success', "Users to be cleaned: {0}".format(remUsers))
    else:
        updateSO(s, 'cleanUsers', 'success', "No Users to be cleaned.")
    logging.info(s['lastOp'])

    



    
