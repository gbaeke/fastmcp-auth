#!/bin/bash

# Azure App Registration Setup Script for FastMCP Auth
# This script creates the necessary app registrations for the React web app and backend API

set -e

echo "🚀 FastMCP Auth - Azure App Registration Setup"
echo "=============================================="

# Check if Azure CLI is installed and user is logged in
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if user is logged in
if ! az account show &> /dev/null; then
    echo "❌ You are not logged in to Azure CLI. Please run 'az login' first."
    exit 1
fi

# Get current subscription info
SUBSCRIPTION_ID=$(az account show --query id --output tsv)
TENANT_ID=$(az account show --query tenantId --output tsv)
TENANT_NAME=$(az account show --query name --output tsv)

echo "📋 Current Azure Context:"
echo "   Subscription: $TENANT_NAME ($SUBSCRIPTION_ID)"
echo "   Tenant ID: $TENANT_ID"
echo ""

read -p "Do you want to continue with this subscription? (y/N): " confirm
if [[ $confirm != [yY] ]]; then
    echo "❌ Setup cancelled. Use 'az account set --subscription <subscription-id>' to switch subscriptions."
    exit 1
fi

echo ""
echo "🔧 Creating App Registrations..."

# Step 1: Create the API app registration
echo ""
echo "1️⃣ Creating Backend API App Registration..."

# Generate a UUID for the scope
SCOPE_UUID=$(uuidgen)

# Create the API app registration first without identifier URIs
API_APP_ID=$(az ad app create \
    --display-name "FastMCP Auth API" \
    --query appId --output tsv)

echo "✅ API App Registration created with ID: $API_APP_ID"

# Set the identifier URI using the app ID (this format is always allowed)
echo "   Setting identifier URI..."
az ad app update --id $API_APP_ID \
    --set identifierUris="[\"api://$API_APP_ID\"]"

# Add OAuth2 permissions (scopes) to the API app
echo "   Adding OAuth2 permissions..."

# Create a temporary JSON file for the OAuth2 permission scope
cat > /tmp/oauth2_scope.json << EOF
[{
    "adminConsentDescription": "Allow the application to access the API on behalf of the signed-in user",
    "adminConsentDisplayName": "Access the API",
    "id": "$SCOPE_UUID",
    "isEnabled": true,
    "type": "User",
    "userConsentDescription": "Allow the application to access the API on your behalf",
    "userConsentDisplayName": "Access the API",
    "value": "access_as_user"
}]
EOF

# Update the API app with OAuth2 permission scopes
az ad app update --id $API_APP_ID \
    --set api.oauth2PermissionScopes=@/tmp/oauth2_scope.json

# Clean up temporary file
rm /tmp/oauth2_scope.json

# Add app roles
echo "   Adding app roles..."

# Create a temporary JSON file for the app role
cat > /tmp/app_role.json << EOF
[{
    "allowedMemberTypes": ["User"],
    "description": "Users can access the API",
    "displayName": "API.Access",
    "isEnabled": true,
    "id": "$(uuidgen)",
    "value": "API.Access"
}]
EOF

# Update the API app with app roles
az ad app update --id $API_APP_ID \
    --set appRoles=@/tmp/app_role.json

# Clean up temporary file
rm /tmp/app_role.json

# Step 2: Create the Web App registration
echo ""
echo "2️⃣ Creating React Web App Registration..."

# Create the web app registration with SPA redirect URIs
WEB_APP_ID=$(az ad app create \
    --display-name "FastMCP Auth Web" \
    --query appId --output tsv)

echo "✅ Web App Registration created with ID: $WEB_APP_ID"

# Update the web app with SPA redirect URIs
echo "   Configuring SPA redirect URIs..."
az ad app update --id $WEB_APP_ID \
    --set spa.redirectUris='["http://localhost:3000"]'

# Configure required resource access
echo "   Configuring API permissions..."

# Create a temporary JSON file for required resource access
cat > /tmp/required_access.json << EOF
[{
    "resourceAppId": "00000003-0000-0000-c000-000000000000",
    "resourceAccess": [{
        "id": "e1fe6dd8-ba31-4d61-89e7-88639da4683d",
        "type": "Scope"
    }]
}, {
    "resourceAppId": "$API_APP_ID",
    "resourceAccess": [{
        "id": "$SCOPE_UUID",
        "type": "Scope"
    }]
}]
EOF

# Update the web app with required resource access
az ad app update --id $WEB_APP_ID \
    --set requiredResourceAccess=@/tmp/required_access.json

# Clean up temporary file
rm /tmp/required_access.json

# Step 3: Grant admin consent for the web app
echo ""
echo "3️⃣ Granting admin consent for permissions..."
sleep 10  # Wait for app registration to propagate

# Get the service principal for the web app (creates it if it doesn't exist)
WEB_SP_ID=$(az ad sp create --id $WEB_APP_ID --query id --output tsv 2>/dev/null || az ad sp show --id $WEB_APP_ID --query id --output tsv)

# Grant admin consent
az ad app permission admin-consent --id $WEB_APP_ID || echo "⚠️  Admin consent may need to be granted manually in the Azure Portal"

echo "✅ Admin consent granted"

# Step 4: Update the authConfig.js file
echo ""
echo "4️⃣ Updating authConfig.js with new app registration details..."

# Create a temporary authConfig.js with the actual values
cat > "$(dirname "$0")/../src/authConfig.js" << EOF
import { LogLevel } from "@azure/msal-browser";

/**
 * Configuration object to be passed to MSAL instance on creation
 * For a full list of MSAL.js configuration parameters, visit:
 * https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md
 */
export const msalConfig = {
    auth: {
        clientId: "$WEB_APP_ID", // Web app client ID
        authority: "https://login.microsoftonline.com/$TENANT_ID", // Your tenant ID
        redirectUri: "http://localhost:3000", // This should match the redirect URI in your app registration
    },
    cache: {
        cacheLocation: "sessionStorage", // This configures where your cache will be stored
        storeAuthStateInCookie: false, // Set this to "true" if you're having issues on IE11 or Edge
    },
    system: {
        loggerOptions: {
            loggerCallback: (level, message, containsPii) => {
                if (containsPii) {
                    return;
                }
                switch (level) {
                    case LogLevel.Error:
                        console.error(message);
                        return;
                    case LogLevel.Info:
                        console.info(message);
                        return;
                    case LogLevel.Verbose:
                        console.debug(message);
                        return;
                    case LogLevel.Warning:
                        console.warn(message);
                        return;
                }
            }
        }
    }
};

/**
 * Scopes you add here will be prompted for user consent during sign-in.
 * By default, MSAL.js will add OIDC scopes (openid, profile, email) to any login request.
 * For more information about OIDC scopes, visit:
 * https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-permissions-and-consent#openid-connect-scopes
 */
export const loginRequest = {
    scopes: ["User.Read"]
};

/**
 * Add here the scopes to request when obtaining an access token for your API
 * The scope below represents the custom API scope for your backend API
 */
export const apiRequest = {
    scopes: ["api://$API_APP_ID/access_as_user"],
    forceRefresh: false // Set this to "true" to skip a cached token and go to the server to get a new token
};

/**
 * API endpoint configuration
 */
export const apiConfig = {
    baseUrl: "http://localhost:8080"
};
EOF

echo "✅ authConfig.js updated with app registration details"

# Step 5: Create environment file for backend
echo ""
echo "5️⃣ Creating environment configuration for backend..."

cat > "$(dirname "$0")/../.env.example" << EOF
# Azure App Registration Configuration
# Copy this file to .env and use these values in your backend API

# Web App Registration
WEB_APP_CLIENT_ID=$WEB_APP_ID

# API App Registration  
API_APP_CLIENT_ID=$API_APP_ID

# Azure Tenant
TENANT_ID=$TENANT_ID

# API Configuration
API_PORT=8080
API_BASE_URL=http://localhost:8080

# CORS Configuration
CORS_ORIGINS=http://localhost:3000
EOF

echo "✅ Environment configuration created at .env.example"

# Step 6: Display summary
echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "📱 Web App Registration:"
echo "   Application ID: $WEB_APP_ID"
echo "   Redirect URI: http://localhost:3000"
echo ""
echo "🔧 API App Registration:"
echo "   Application ID: $API_APP_ID"
echo "   Identifier URI: api://$API_APP_ID"
echo "   Scope: api://$API_APP_ID/access_as_user"
echo ""
echo "🏢 Azure Tenant:"
echo "   Tenant ID: $TENANT_ID"
echo ""
echo "📋 Next Steps:"
echo "1. Copy .env.example to .env and configure your backend API with these values"
echo "2. Run 'npm install' in the web directory to install dependencies"
echo "3. Run 'npm start' to start the React development server on http://localhost:3000"
echo "4. Implement your backend API to accept Bearer tokens from the web app"
echo ""
echo "🌐 Azure Portal Links:"
echo "   Web App: https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/Overview/appId/$WEB_APP_ID"
echo "   API App: https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/Overview/appId/$API_APP_ID"
echo ""
echo "⚠️  Important Notes:"
echo "   - The authConfig.js file has been automatically updated with your app registration details"
echo "   - Make sure your backend API validates JWT tokens from Azure AD"
echo "   - The API should be configured to accept the audience: api://$API_APP_ID"
echo "   - Grant admin consent in Azure Portal if the automatic consent failed"
echo ""
