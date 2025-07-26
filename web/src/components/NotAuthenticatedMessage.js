import React from 'react';
import { useMsal } from "@azure/msal-react";
import { loginRequest } from "../authConfig";
import '../styles/NotAuthenticatedMessage.css';

/**
 * Component displayed when user is not authenticated
 */
const NotAuthenticatedMessage = () => {
    const { instance } = useMsal();

    const handleLogin = () => {
        instance.loginRedirect(loginRequest).catch(e => {
            console.error(e);
        });
    };

    return (
        <div className="not-authenticated-container">
            <div className="not-authenticated-card">
                <div className="lock-icon">
                    🔒
                </div>
                <h2>Authentication Required</h2>
                <p className="message">
                    You are not currently signed in. Please authenticate with your Azure account to access this application.
                </p>
                <div className="features-list">
                    <h3>What you can do after signing in:</h3>
                    <ul>
                        <li>✓ Access your personalized dashboard</li>
                        <li>✓ Call protected backend APIs</li>
                        <li>✓ Manage your profile and settings</li>
                        <li>✓ Secure data synchronization</li>
                    </ul>
                </div>
                <button 
                    className="sign-in-button" 
                    onClick={handleLogin}
                >
                    Sign In with Azure
                </button>
                <div className="security-notice">
                    <small>
                        🛡️ Your data is protected with enterprise-grade Azure security
                    </small>
                </div>
            </div>
        </div>
    );
};

export default NotAuthenticatedMessage;
