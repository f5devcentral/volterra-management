from az.cli import az
import os, configparser

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'funcConfig.ini'))

def checkVars(section: dict):
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
    for v in required_vars:
        required_vars[v] = section[v], False

        if required_vars[v] == False:
            raise ValueError("A value must be provided for {0}".format(v))

def kvSecret(vault: str, name: str, value:str):
    azCommand("keyvault create \
        --vault-name {0} \
        --name {1} \
        --value {2}"
        .format(vault, name, value)
    )

def appSetting(name:str, resourceGroup: str, settings: str):
    azCommand("functionapp config appsettings set \
        --name {0} \
        --resource-group {1} \
        --settings {2}"
        .format(name, resourceGroup, settings) 
    )

def azCommand(command: str):
    res = az(command)
    if res[0]:
        raise RuntimeError("Azure Client Error: {0}".format(res[2]))
    return res[1]


def deployBase(section: dict):
    secrets = {
        "VoltTenantName" : section['VoltTenantName'],
        "VoltTenantApiToken" : section['VoltTenantApiToken'],
        "VoltTenantTokenName" : section['VoltTenantTokenName'],
        "AADclientID" : section['AADclientID'],
        "AADtenantID" : section['AADtenantID'],
        "AADsecret" : section['AADsecret'],
        "AADGroupName" : section['AADGroupName']
    }

    azCommand("group create \
        --name {0} \
        --location {1}"
        .format(section['ResourceGroupName'], section['region'])
    )

    azCommand("storage account create \
        --name {0} \
        --location {1} \
        --resource-group {2} \
        --sku Standard_LRS"
        .format(section['StorageName'], section['Region'], section['ResourceGroupName'])
    )

    azCommand("keyvault create \
        --name {0} \
        --resource-group {1} \
        --location {2}"
        .format(section['KeyVaultName'], section['ResourceGroupName'], section['Region'])
    )

    for s in secrets:
        kvSecret(section['KeyVaultName'], s, secrets[s])

    azCommand("functionapp create \
        --name {0} \
        --storage-account {1} \
        --consumption-plan-location {2} \
        --resource-group {3} \
        --os-type linux \
        --functions-version 3 \
        --runtime python"
        .format(section['FunctionAppName'], section['StorageName'], section['Region'], section['ResourceGroupName'])
    )

    azCommand("functionapp identity assign \
        --resource-group {0} \
        --name {1}"
        .format(section['ResourceGroupName'], section['FunctionAppName'])
    )

    principalId = azCommand("functionapp identity show \
                      --resource-group {0} \
                      --name {1} \
                      --query principalId \
                      -o tsv"
                      .format(section['FunctionAppName'], section['ResourceGroupName'])
                    )
    
    azCommand("keyvault set policy \
        --name {0} \
        --resource-group {1} \
        --object-id {2} \
        -secret-permission get list"
        .format(section['KeyVaultName'], section['ResourceGroupName'], principalId)
    )

    for a in secrets:
        appSetting(a, section['ResourceGroupName'], secrets[a])


def main():
    for section in config.sections():
        checkVars(section)
        deployBase(section)
