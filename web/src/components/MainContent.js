import React from 'react';
import { AuthenticatedTemplate, UnauthenticatedTemplate } from "@azure/msal-react";
import TopBar from './TopBar';
import WelcomeMessage from './WelcomeMessage';
import NotAuthenticatedMessage from './NotAuthenticatedMessage';

/**
 * MainContent component that renders different content based on authentication state
 */
const MainContent = () => {
    return (
        <div>
            <TopBar />
            <main className="main-content">
                <AuthenticatedTemplate>
                    <WelcomeMessage />
                </AuthenticatedTemplate>
                <UnauthenticatedTemplate>
                    <NotAuthenticatedMessage />
                </UnauthenticatedTemplate>
            </main>
        </div>
    );
};

export default MainContent;
