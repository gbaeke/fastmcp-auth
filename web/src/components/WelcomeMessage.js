import React, { useState } from 'react';
import { useMsal } from "@azure/msal-react";
import { apiRequest, apiConfig } from "../authConfig";
import '../styles/WelcomeMessage.css';

/**
 * Component displayed when user is authenticated
 */
const WelcomeMessage = () => {
    const { instance, accounts } = useMsal();
    const [apiResponse, setApiResponse] = useState(null);
    const [apiError, setApiError] = useState(null);
    const [isLoading, setIsLoading] = useState(false);

    const account = accounts[0];

    const callApi = async () => {
        setIsLoading(true);
        setApiError(null);
        setApiResponse(null);

        try {
            // Silently acquire an access token which is then attached to a request for the API
            const response = await instance.acquireTokenSilent({
                ...apiRequest,
                account: account
            });

            // Call your API with the access token
            const apiResult = await fetch(`${apiConfig.baseUrl}/reverse`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${response.accessToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ input_string: "demo string" })
            });

            if (apiResult.ok) {
                const data = await apiResult.json();
                setApiResponse(data);
            } else {
                setApiError(`API call failed with status: ${apiResult.status}`);
            }
        } catch (error) {
            console.error('API call error:', error);
            setApiError(error.message || 'An error occurred while calling the API');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="welcome-container">
            <div className="welcome-card">
                <h2>Welcome to FastMCP Auth!</h2>
                <p className="welcome-text">
                    You are successfully signed in. Your authentication token can be used to access protected APIs.
                </p>
                
                <div className="user-details">
                    <h3>User Information</h3>
                    <div className="user-info-grid">
                        <div className="info-item">
                            <label>Name:</label>
                            <span>{account?.name || 'Not available'}</span>
                        </div>
                        <div className="info-item">
                            <label>Email:</label>
                            <span>{account?.username || 'Not available'}</span>
                        </div>
                        <div className="info-item">
                            <label>Account ID:</label>
                            <span className="account-id">{account?.homeAccountId || 'Not available'}</span>
                        </div>
                    </div>
                </div>

                <div className="api-test-section">
                    <h3>API Test</h3>
                    <p>Test your authentication by calling the backend API:</p>
                    
                    <button 
                        className="api-test-button" 
                        onClick={callApi}
                        disabled={isLoading}
                    >
                        {isLoading ? 'Calling API...' : 'Call Backend API'}
                    </button>

                    {apiResponse && (
                        <div className="api-response success">
                            <h4>API Response:</h4>
                            <pre>{JSON.stringify(apiResponse, null, 2)}</pre>
                        </div>
                    )}

                    {apiError && (
                        <div className="api-response error">
                            <h4>API Error:</h4>
                            <p>{apiError}</p>
                            <small>Note: The backend API might not be running yet.</small>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default WelcomeMessage;
