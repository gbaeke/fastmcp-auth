
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
import requests
from typing import Optional


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Azure AD config from web/src/authConfig.js
TENANT_ID = "484588df-21e4-427c-b2a5-cc39d6a73281"
API_CLIENT_ID = "f9ca7d53-fd9c-4e71-83f1-55f4644a75d6"  # API app registration client ID
API_AUDIENCE = f"api://{API_CLIENT_ID}"  # Expected audience format based on authConfig.js
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
JWKS_URL = f"{AUTHORITY}/discovery/v2.0/keys"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_jwks():
    resp = requests.get(JWKS_URL)
    resp.raise_for_status()
    return resp.json()

def verify_jwt(token: str):
    """Verify the JWT token is from Entra ID (minimal validation)"""
    from jose.utils import base64url_decode
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization

    try:
        # Get the token header to find the key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No key ID in token header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get the matching key from Microsoft's JWKS endpoint
        jwks = get_jwks()
        key = None
        for potential_key in jwks["keys"]:
            if potential_key["kid"] == kid:
                key = potential_key
                break
        
        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Key not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Build the public key
        n_b64 = key["n"].encode("utf-8") if isinstance(key["n"], str) else key["n"]
        e_b64 = key["e"].encode("utf-8") if isinstance(key["e"], str) else key["e"]
        n = int.from_bytes(base64url_decode(n_b64), "big")
        e = int.from_bytes(base64url_decode(e_b64), "big")
        public_key = rsa.RSAPublicNumbers(e, n).public_key(default_backend())
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Verify signature, audience and issuer
        payload = jwt.decode(
            token, 
            public_pem, 
            algorithms=["RS256"],
            audience=API_AUDIENCE,  # Use the audience from config: api://CLIENT_ID
            # Azure AD v2.0 tokens use this issuer format
            issuer=f"https://sts.windows.net/{TENANT_ID}/"  # Verify token comes from the correct Entra ID tenant
        )
        
        return payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation error: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(token: str = Depends(oauth2_scheme)):
    return verify_jwt(token)

@app.post("/reverse")
async def reverse_string(request: Request, user: dict = Depends(get_current_user)):
    # Parse the request body
    body = await request.json()
    
    # Extract input_string from the body
    input_string = body.get("input_string", "")
    if not input_string:
        raise HTTPException(status_code=400, detail="input_string is required")
        
    return {"reversed": input_string[::-1]}

@app.post("/reverse-noauth")
async def reverse_string_noauth(request: Request):
    # Parse the request body
    body = await request.json()
    
    # Extract input_string from the body
    input_string = body.get("input_string", "")
    if not input_string:
        raise HTTPException(status_code=400, detail="input_string is required")
        
    return {"reversed": input_string[::-1]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8880, reload=True)
