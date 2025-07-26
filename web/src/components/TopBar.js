import React from 'react';
import { AuthenticatedTemplate, UnauthenticatedTemplate, useMsal } from "@azure/msal-react";
import { loginRequest } from "../authConfig";
import '../styles/TopBar.css';

/**
 * TopBar component that shows login/logout options
 */
const TopBar = () => {
    const { instance, accounts } = useMsal();

    const handleLogin = (loginType) => {
        if (loginType === "popup") {
            instance.loginPopup(loginRequest).catch(e => {
                console.error(e);
            });
        } else if (loginType === "redirect") {
            instance.loginRedirect(loginRequest).catch(e => {
                console.error(e);
            });
        }
    };

    const handleLogout = (logoutType) => {
        if (logoutType === "popup") {
            instance.logoutPopup({
                postLogoutRedirectUri: "/",
                mainWindowRedirectUri: "/"
            });
        } else if (logoutType === "redirect") {
            instance.logoutRedirect({
                postLogoutRedirectUri: "/"
            });
        }
    };

    return (
        <nav className="top-bar">
            <div className="top-bar-content">
                <div className="logo">
                    <h1>FastMCP Auth</h1>
                </div>
                <div className="auth-section">
                    <AuthenticatedTemplate>
                        <div className="user-info">
                            <span className="welcome-text">
                                Welcome, {accounts[0] && accounts[0].name}
                            </span>
                            <button 
                                className="auth-button logout-button" 
                                onClick={() => handleLogout("redirect")}
                            >
                                Sign Out
                            </button>
                        </div>
                    </AuthenticatedTemplate>
                    <UnauthenticatedTemplate>
                        <button 
                            className="auth-button login-button" 
                            onClick={() => handleLogin("redirect")}
                        >
                            Sign In
                        </button>
                    </UnauthenticatedTemplate>
                </div>
            </div>
        </nav>
    );
};

export default TopBar;
