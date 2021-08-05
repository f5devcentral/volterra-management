import datetime
import logging
import os

from AAD_helpers import retrieveAccessToken, voltUsers2Add
from ms_graph import getUser
from volterra_helpers import createVoltSession, addUser, cleanUserRoles

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
    cleanUserRoles(s)
    logging.info(s['lastOp'])

    # Add Users from AAD
    AADtoken = retrieveAccessToken(required_vars['AADclientID'], required_vars['AADtenantID'], required_vars['AADsecret'])
    addUsers = voltUsers2Add(s, AADtoken, required_vars['AADGroupName'])
    for user in addUsers:
        email = user['userPrincipalName']
        thisUser = getUser(AADtoken, email)
        addUser(s, email, thisUser['givenName'], thisUser['surname'])
        logging.info(s['lastOp'])
    



    
