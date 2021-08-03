import sys
import json
import logging
import msal


def retrieveAccessToken(client_id, tenant_id, secret):
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