from az.cli import az
import os, configparser

def checkVars(config):
    required_vars = {
        'AADclientID': False,
        'AADtenantID': False,
        'AADsecret': False,
        'AADGroupName': False,
        'VoltTenantApiToken': False,
        'VoltTenantTokenName': False,
        'VoltTenantName': False,
        'Region': False,
        'ResourceGroupName': False,
        'StorageName': False,
        'KeyVaultName': False,
        'FunctionAppName': False
    }
    for s in config.sections():
        for v in required_vars:
            required_vars[v] = config.has_option(s, v)
        
        if required_vars[v] == False:
            raise ValueError("A value must be provided for: {0} in section: {1}".format(v, s))

def kvSecret(vault: str, name: str, value: str):
    return azCommand("keyvault secret set --vault-name {0} --name {1} --value {2}".format(vault, name, value))

def appSetting(name: str, vault: str, function: str, resourceGroup: str):
    settingURI = azCommand("keyvault secret show --vault-name {0} --name {1} --query id".format(vault, name))
    return azCommand('functionapp config appsettings set --name {0} --resource-group {1} --settings "{2}=@Microsoft.KeyVault(SecretUri={3})"'.format(function, resourceGroup, name, settingURI))

def azCommand(command: str):
    res = az(command)
    if res[0]:
        raise RuntimeError(res[2])
    return res[1]

def azCmdNoError(command: str):
    res = az(command)
    #NOTE:: Intentionally returning the entire dict response (in case we need to do something else with it)
    return res

def deployBase(section):
    secrets = {
        "VoltTenantName" : section['VoltTenantName'],
        "VoltTenantApiToken" : section['VoltTenantApiToken'],
        "VoltTenantTokenName" : section['VoltTenantTokenName'],
        "AADclientID" : section['AADclientID'],
        "AADtenantID" : section['AADtenantID'],
        "AADsecret" : section['AADsecret'],
        "AADGroupName" : section['AADGroupName']
    }

    createRG = "group create --name {0} --location {1}" \
        .format(section['ResourceGroupName'], section['Region'])
    azCommand(createRG)

    createSA = "storage account create --name {0} --location {1} --resource-group {2} --sku Standard_LRS" \
        .format(section['StorageName'], section['Region'], section['ResourceGroupName'])
    azCommand(createSA)

    #KeyVaults are, evidently, **not** idempotent in the Azure CLI. We need treat them differently.    
    createKV = "keyvault create --name {0} --resource-group {1} --location {2}" \
        .format(section['KeyVaultName'], section['ResourceGroupName'], section['Region'])
    
    try:
        azCommand(createKV)
    except:
        print("KeyVault likely already exists. Skipping creation.")
        pass

    for s in secrets:
        kvSecret(section['KeyVaultName'], s, secrets[s])

    createApp = "functionapp create --name {0} --storage-account {1} --consumption-plan-location {2} --resource-group {3} --os-type linux --functions-version 3 --runtime python" \
        .format(section['FunctionAppName'], section['StorageName'], section['Region'], section['ResourceGroupName'])
    azCommand(createApp)

    appId = "functionapp identity assign --resource-group {0} --name {1}" \
        .format(section['ResourceGroupName'], section['FunctionAppName'])
    azCommand(appId)

    principalId = azCommand("functionapp identity show --resource-group {0} --name {1} --query principalId".format(section['ResourceGroupName'], section['FunctionAppName']))
    
    kvPolicy = "keyvault set-policy --name {0} --resource-group {1} --object-id {2} --secret-permission get list" \
        .format(section['KeyVaultName'], section['ResourceGroupName'], principalId)
    azCommand(kvPolicy)

    for a in secrets:
        appSetting(a, section['KeyVaultName'], section['FunctionAppName'], section['ResourceGroupName'])


def main():
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'funcConfig.ini'))
    checkVars(config)
    for section in config.sections():
        deployBase(config[section])
        print("Deployment for {0} complete.".format(section))
    print("All Deployments Complete.")

if __name__ == "__main__":
    main()
