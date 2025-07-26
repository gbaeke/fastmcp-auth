# FastMCP Auth - React Web Application with Azure Entra ID

A professional React web application with Azure Entra ID authentication, designed to work with a backend API. The application features a clean, modern UI with proper authentication state management.

## Features

- 🔐 **Azure Entra ID Authentication** - Secure login/logout with Microsoft accounts
- 🎨 **Modern UI Design** - Professional gradient design with glassmorphism effects
- 📱 **Responsive Layout** - Works on desktop and mobile devices
- 🔄 **Authentication State Management** - Different views for authenticated/unauthenticated users
- 🌐 **API Integration Ready** - Pre-configured to call backend APIs with Bearer tokens
- ⚡ **React 18** - Built with the latest React features
- 🛡️ **MSAL React** - Official Microsoft authentication library for React

## Quick Start

### Prerequisites

- Node.js 16+ and npm
- Azure CLI installed and configured
- An Azure subscription with permission to create app registrations

### 1. Setup Azure App Registrations

Run the automated setup script to create the necessary Azure app registrations:

\`\`\`bash
# Make sure you're logged in to Azure CLI
az login

# Run the setup script
./setup-azure-apps.sh
\`\`\`

This script will:
- Create a web app registration for the React application
- Create an API app registration for your backend
- Configure proper permissions and scopes
- Update the `authConfig.js` file with your app registration details
- Generate an `.env.example` file for your backend configuration

### 2. Install Dependencies

\`\`\`bash
npm install
\`\`\`

### 3. Start the Development Server

\`\`\`bash
npm start
\`\`\`

The application will start on `http://localhost:3000`.

## Manual Azure Setup (Alternative)

If you prefer to set up the app registrations manually:

### 1. Create API App Registration

1. Go to [Azure Portal](https://portal.azure.com) → Microsoft Entra ID → App registrations
2. Click "New registration"
3. Name: "FastMCP Auth API"
4. Account types: "Accounts in this organizational directory only"
5. Don't set a redirect URI
6. Click "Register"
7. Go to "Expose an API"
8. Set Application ID URI to: `api://fastmcp-auth-api`
9. Add a scope:
   - Scope name: `access_as_user`
   - Admin consent display name: "Access the API"
   - Admin consent description: "Allow the application to access the API on behalf of the signed-in user"
   - State: Enabled

### 2. Create Web App Registration

1. Click "New registration"
2. Name: "FastMCP Auth Web"
3. Account types: "Accounts in this organizational directory only"
4. Redirect URI: "Single-page application (SPA)" → `http://localhost:3000`
5. Click "Register"
6. Go to "API permissions"
7. Add permissions:
   - Microsoft Graph → Delegated → User.Read
   - Your API (FastMCP Auth API) → access_as_user
8. Grant admin consent

### 3. Update Configuration

Update `src/authConfig.js` with your app registration details:

\`\`\`javascript
export const msalConfig = {
    auth: {
        clientId: "YOUR_WEB_APP_CLIENT_ID",
        authority: "https://login.microsoftonline.com/YOUR_TENANT_ID",
        redirectUri: "http://localhost:3000",
    },
    // ...
};

export const apiRequest = {
    scopes: ["api://fastmcp-auth-api/access_as_user"],
    // ...
};
\`\`\`

## Project Structure

\`\`\`
web/
├── public/
│   ├── index.html          # Main HTML template
│   └── manifest.json       # PWA manifest
├── src/
│   ├── components/
│   │   ├── MainContent.js  # Main content component with auth templates
│   │   ├── TopBar.js       # Navigation bar with login/logout
│   │   ├── WelcomeMessage.js     # Authenticated user view
│   │   └── NotAuthenticatedMessage.js  # Unauthenticated user view
│   ├── styles/
│   │   ├── TopBar.css
│   │   ├── WelcomeMessage.css
│   │   └── NotAuthenticatedMessage.css
│   ├── App.js              # Main app component with MSAL provider
│   ├── authConfig.js       # MSAL configuration
│   └── index.js            # App entry point
├── package.json
└── setup-azure-apps.sh    # Automated Azure setup script
\`\`\`

## Environment Variables

The setup script creates a `.env.example` file with the following structure for your backend:

\`\`\`env
# Azure App Registration Configuration
WEB_APP_CLIENT_ID=your-web-app-id
API_APP_CLIENT_ID=your-api-app-id
TENANT_ID=your-tenant-id

# API Configuration
API_PORT=8080
API_BASE_URL=http://localhost:8080
CORS_ORIGINS=http://localhost:3000
\`\`\`

## Backend API Integration

The React app is configured to call a backend API at `http://localhost:8080`. When calling the API, it automatically includes the Azure access token in the Authorization header:

\`\`\`javascript
const response = await fetch('/api/endpoint', {
    headers: {
        'Authorization': \`Bearer \${accessToken}\`,
        'Content-Type': 'application/json'
    }
});
\`\`\`

Your backend API should:
1. Validate JWT tokens from Azure AD
2. Check the audience claim matches: `api://fastmcp-auth-api`
3. Verify the token signature using Azure's public keys
4. Extract user information from token claims

## UI Features

### Unauthenticated State
- Professional "not authenticated" message
- List of features available after login
- Prominent sign-in button
- Security assurance messaging

### Authenticated State
- Welcome message with user information
- User details display (name, email, account ID)
- API test functionality
- Secure logout option

### Top Navigation
- Application branding
- Context-aware login/logout button
- User welcome message when authenticated

## Development

### Available Scripts

- `npm start` - Start development server
- `npm build` - Build for production
- `npm test` - Run tests
- `npm run eject` - Eject from Create React App

### Customization

1. **Styling**: Modify CSS files in `src/styles/` to customize the appearance
2. **Authentication Flow**: Update `authConfig.js` for different auth scenarios
3. **API Integration**: Modify `WelcomeMessage.js` to change API testing behavior
4. **Branding**: Update colors, logos, and text throughout the components

## Security Considerations

- Access tokens are stored in session storage (configurable)
- All API calls include proper authentication headers
- MSAL handles token refresh automatically
- Redirect URIs are restricted to localhost for development

## Troubleshooting

### Common Issues

1. **"AADSTS50011: The reply URL specified in the request does not match"**
   - Ensure redirect URI in app registration matches exactly: `http://localhost:3000`

2. **"AADSTS65001: The user or administrator has not consented"**
   - Grant admin consent in Azure Portal → App registrations → API permissions

3. **API calls failing with 401**
   - Verify backend is validating tokens correctly
   - Check audience claim in token matches API identifier URI

4. **Slow token acquisition**
   - Check network connectivity to Azure endpoints
   - Verify tenant ID and client ID are correct

### Debug Mode

Enable debug logging by modifying `authConfig.js`:

\`\`\`javascript
system: {
    loggerOptions: {
        logLevel: LogLevel.Verbose, // Change to Verbose for detailed logs
        // ...
    }
}
\`\`\`

## Production Deployment

Before deploying to production:

1. Update redirect URIs in Azure app registration
2. Configure proper CORS origins for your backend
3. Use HTTPS for all endpoints
4. Consider using `localStorage` instead of `sessionStorage` for token caching
5. Implement proper error handling and user feedback
6. Add loading states and proper UX flows

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly with different auth scenarios
5. Submit a pull request

## License

This project is licensed under the MIT License.
