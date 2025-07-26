import React, { useEffect } from 'react';
import { onMcpAuthorization } from 'use-mcp';

/**
 * Component to handle OAuth callback for MCP server authentication
 */
const OAuthCallback = () => {
    useEffect(() => {
        // Process the OAuth callback and close the window
        onMcpAuthorization();
    }, []);

    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100vh',
            padding: '2rem'
        }}>
            <h1>Authenticating...</h1>
            <p>This window should close automatically after authentication completes.</p>
        </div>
    );
};

export default OAuthCallback;
