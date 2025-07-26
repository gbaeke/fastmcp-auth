import { LogLevel } from "@azure/msal-browser";

/**
 * Configuration object to be passed to MSAL instance on creation
 * For a full list of MSAL.js configuration parameters, visit:
 * https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md
 */
export const msalConfig = {
    auth: {
        clientId: process.env.REACT_APP_CLIENT_ID, // This is the client ID of your web app registration
        authority: process.env.REACT_APP_AUTHORITY, // This is your tenant ID
        redirectUri: process.env.REACT_APP_REDIRECT_URI, // This should match the redirect URI in your app registration
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
    scopes: process.env.REACT_APP_LOGIN_SCOPES ? process.env.REACT_APP_LOGIN_SCOPES.split(' ') : ["User.Read"]
};

/**
 * Add here the scopes to request when obtaining an access token for your API
 * The scope below represents the custom API scope for your backend API
 */
export const apiRequest = {
    scopes: process.env.REACT_APP_API_SCOPES ? process.env.REACT_APP_API_SCOPES.split(' ') : ["api://f9ca7d53-fd9c-4e71-83f1-55f4644a75d6/execute"],
    forceRefresh: false // Set this to "true" to skip a cached token and go to the server to get a new token
};

/**
 * API endpoint configuration
 */
export const apiConfig = {
    baseUrl: process.env.REACT_APP_API_BASE_URL
};
