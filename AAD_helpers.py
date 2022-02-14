from ms_graph import getGroupId, getGroupMembers
import logging
import msal

def retrieveAccessToken(client_id: str, tenant_id: str, secret: str) -> str:
    authority = f'https://login.microsoftonline.com/{tenant_id}'
    app = None
    result = None

    scope = ["https://graph.microsoft.com/.default"]
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=secret
    )
    result = app.acquire_token_silent(scope, account=None)

    result = app.acquire_token_for_client(scopes=scope)

    if "access_token" in result:
        return result['access_token']
    else:
        logging.info(result.get("error"))
        logging.info(result.get("error_description"))
        logging.info(result.get("correlation_id"))
        return None

def getAADGroupMembers(token: str, AADGroupName: str) -> list:
    id = getGroupId(token, AADGroupName)
    res = getGroupMembers(token, id)
    return res

def voltUsers2Add(session: dict, token: str, AADGroupNames: list, role: str) -> list:
    users = []
    for AADGroupName in AADGroupNames:
        AADGroupMembers: list[type[dict]] = getAADGroupMembers(token, AADGroupName)
        # Build comparable VoltConsole user list
        voltUserList = []
        for user in session['cache']['users']:
            voltUserList.append({
                'userPrincipalName': user['email']
            }) 
        # Normalize AAD and VoltConsole user lists
        for user in AADGroupMembers:
            user['userPrincipalName'] = user['userPrincipalName'].lower()
            del user['givenName']
            del user['surname']

        for user in voltUserList:
            user['userPrincipalName'] = user['userPrincipalName'].lower()
        # Compare lists 
        res = [x for x in AADGroupMembers if x not in voltUserList]
        for user in res:
            users.append({
                'userPrincipalName': user['userPrincipalName'],
                'role': role
            })
    return users

def voltUsers2Remove(session: dict, token: str, AADGroupNames: list) -> list:
    users = []
    for AADGroupName in AADGroupNames:
        AADGroupMembers = getAADGroupMembers(token, AADGroupName)
        # Build comparable VoltConsole user list
        voltUserList = []
        for user in session['cache']['users']:
            voltUserList.append({
                'userPrincipalName': user['email']
            }) 
        # Normalize AAD and VoltConsole user lists
        for user in AADGroupMembers:
            user['userPrincipalName'] = user['userPrincipalName'].lower()
            del user['givenName']
            del user['surname']

        for user in voltUserList:
            user['userPrincipalName'] = user['userPrincipalName'].lower()
        # Compare lists 
        res = [x for x in voltUserList if x not in AADGroupMembers]
        for user in res:
            users.append(user)
    return users
    

