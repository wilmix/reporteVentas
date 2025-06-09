import requests
import os
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs, unquote, urljoin # Added urljoin
import re # Added for regex parsing

# === CARGAR VARIABLES DE ENTORNO ===
load_dotenv()

# Credentials
SIAT_NIT = os.environ.get("SIAT_NIT")
SIAT_EMAIL = os.environ.get("SIAT_EMAIL")
SIAT_PASSWORD = os.environ.get("SIAT_PASSWORD")

# Device ID (user must get this from their browser's network request payload)
SIAT_DEVICE_ID_RAW = os.environ.get("SIAT_DEVICE_ID_RAW")

# Client ID (usually fixed for the application)
SIAT_CLIENT_ID = os.environ.get("SIAT_CLIENT_ID", "app-frontend")


# Validate essential variables that MUST come from .env
required_env_vars = {
    "SIAT_NIT": SIAT_NIT,
    "SIAT_EMAIL": SIAT_EMAIL,
    "SIAT_PASSWORD": SIAT_PASSWORD,
    "SIAT_DEVICE_ID_RAW": SIAT_DEVICE_ID_RAW,
}

missing_vars = [name for name, value in required_env_vars.items() if not value]

if missing_vars:
    error_message = "Faltan las siguientes variables de entorno en tu archivo .env:\\n"
    for var_name in missing_vars:
        error_message += f"{var_name}=TU_VALOR_AQUI\\n"
    if not SIAT_DEVICE_ID_RAW: # Specifically check if SIAT_DEVICE_ID_RAW was missing
         error_message += "\\nEjemplo para SIAT_DEVICE_ID_RAW (sin codificar URL, obtenlo de tu navegador al inspeccionar la petición de login):\n"
         error_message += "SIAT_DEVICE_ID_RAW=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36|es-ES|240|Win32|7|Desktop|Chrome\\n"
    raise RuntimeError(error_message)

# === URLS and Initial Setup ===
# Initial URL to fetch the login page and dynamic tokens
# Changed redirect_uri to point to the SIAT launcher, which is a more common redirect for this portal.
INITIAL_AUTH_URL = f"https://login.impuestos.gob.bo/realms/login2/protocol/openid-connect/auth?client_id={SIAT_CLIENT_ID}&redirect_uri=https%3A%2F%2Fsiat.impuestos.gob.bo%2Fv2%2Flauncher%2F&state=dummy_state&response_mode=fragment&response_type=code&scope=openid&nonce=dummy_nonce"

# === HEADERS for initial GET request ===
GET_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.5",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

session = requests.Session()
# Update User-Agent for the whole session
session.headers.update({"User-Agent": GET_HEADERS["User-Agent"]})


try:
    print(f"Step 1: Fetching login page from: {INITIAL_AUTH_URL}")
    get_response = session.get(INITIAL_AUTH_URL, headers=GET_HEADERS, allow_redirects=True)
    get_response.raise_for_status()
    login_page_html = get_response.text
    actual_login_page_url = get_response.url # URL after any redirects, this will be our Referer

    print(f"Successfully fetched login page. Actual URL: {actual_login_page_url}")

    # Attempt to find the form action URL using regex (common for Keycloak)
    match = re.search(r'<form\s+[^>]*id="kc-form-login"[^>]*action="([^"]+)"[^>]*>', login_page_html, re.IGNORECASE)
    if not match: # Fallback to a more generic form search
        match = re.search(r'<form\s+[^>]*action="([^"]+)"[^>]*method="post"[^>]*>', login_page_html, re.IGNORECASE)

    if not match:
        print("[ERROR] Could not find login form action URL in the page HTML.")
        print("Page HTML (first 1000 chars):", login_page_html[:1000])
        raise RuntimeError("Failed to parse login form action URL.")

    form_action_url_relative = match.group(1).replace("&amp;", "&") # Replace HTML entities
    # Resolve the action URL (it might be relative) against the page's URL
    form_action_url_absolute = urljoin(actual_login_page_url, form_action_url_relative)
    
    print(f"Found form action URL: {form_action_url_absolute}")

    parsed_action_url = urlparse(form_action_url_absolute)
    query_params_from_action = parse_qs(parsed_action_url.query)

    # Extract dynamic tokens for the POST request's URL parameters
    extracted_session_code = query_params_from_action.get("session_code", [None])[0]
    extracted_execution = query_params_from_action.get("execution", [None])[0]
    extracted_client_id = query_params_from_action.get("client_id", [SIAT_CLIENT_ID])[0] # Use from form or default
    extracted_tab_id = query_params_from_action.get("tab_id", [None])[0]

    if not all([extracted_session_code, extracted_execution, extracted_tab_id]):
        print("[ERROR] Could not extract all required dynamic tokens (session_code, execution, tab_id) from form action URL.")
        print(f"  Parsed query_params from action URL: {query_params_from_action}")
        raise RuntimeError("Failed to extract dynamic tokens from login page.")

    print(f"Extracted tokens: session_code={extracted_session_code}, execution={extracted_execution}, client_id={extracted_client_id}, tab_id={extracted_tab_id}")

    # The base URL for POST is the scheme, netloc, and path from the parsed action URL
    post_url_base = f"{parsed_action_url.scheme}://{parsed_action_url.netloc}{parsed_action_url.path}"

    # === HEADERS for POST request ===
    POST_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "es-ES,es;q=0.5",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": parsed_action_url.netloc,
        "Origin": f"{parsed_action_url.scheme}://{parsed_action_url.netloc}",
        "Pragma": "no-cache",
        "Referer": actual_login_page_url, # Referer is the URL of the page that contained the form
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Sec-GPC": "1",
        "Upgrade-Insecure-Requests": "1",
        # User-Agent is already set for the session
        "sec-ch-ua": '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"'
    }

    # === LOGIN PAYLOAD (FORM DATA) ===
    # Based on your initial network capture
    login_payload = {
        "nitCur": SIAT_NIT,
        "email": SIAT_EMAIL,
        "deviceId": SIAT_DEVICE_ID_RAW, # requests will URL-encode this
        "password": SIAT_PASSWORD,
        # "username": SIAT_EMAIL, # If the form uses 'username' instead of nitCur/email
    }

    # === URL PARAMETERS for POST request (query string part) ===
    post_url_params = {
        "session_code": extracted_session_code,
        "execution": extracted_execution,
        "client_id": extracted_client_id,
        "tab_id": extracted_tab_id
    }

    print(f"\\nStep 2: Attempting login to: {post_url_base}")
    print(f"URL Params for POST: {post_url_params}")
    print(f"Payload for POST: {login_payload}")
    # print(f"Headers for POST: {POST_HEADERS}") # Can be verbose

    response = session.post(
        post_url_base,
        params=post_url_params,
        data=login_payload,
        headers=POST_HEADERS,
        allow_redirects=False # Important to see the 302 redirect
    )

    print(f"\\n--- Response ---")
    print(f"Status Code: {response.status_code}")
    print("\\nResponse Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")

    if response.status_code == 302:
        redirect_location = response.headers.get('Location')
        print(f"\\nRedirecting to: {redirect_location}")
        if redirect_location and "launcher" in redirect_location:
            print("Login likely SUCCESSFUL, redirecting to launcher.")

            # --- NEW STEP: Navigate to RVCC page ---
            rvcc_url = "https://rvcc.impuestos.gob.bo/rvcc/index.xhtml"
            print(f"\\nStep 3: Navigating to RVCC page: {rvcc_url}")
            try:
                rvcc_response = session.get(rvcc_url, headers=GET_HEADERS, allow_redirects=True) # Use GET_HEADERS or a simplified version
                rvcc_response.raise_for_status() # Check for HTTP errors
                print(f"Successfully fetched RVCC page. Status: {rvcc_response.status_code}")
                print(f"Actual RVCC page URL: {rvcc_response.url}")
                
                rvcc_page_html = rvcc_response.text
                print("\\nRVCC Page Content (first 1000 chars):")
                print(rvcc_page_html[:1000])

                if "REGISTRO DE COMPRAS Y VENTAS" in rvcc_page_html:
                    print("\\n[SUCCESS] Successfully landed on the RVCC page and found 'REGISTRO DE COMPRAS Y VENTAS'.")
                else:
                    print("\\n[WARNING] Landed on RVCC page, but did not find 'REGISTRO DE COMPRAS Y VENTAS'. Check content.")
                
            except requests.exceptions.RequestException as e_rvcc:
                print(f"[ERROR] Could not fetch RVCC page: {e_rvcc}")
            # --- END OF NEW STEP ---

        elif redirect_location and "error" in redirect_location.lower():
            print(f"[WARNING] Login might have failed. Redirect location contains an error: {redirect_location}")
        else:
            print("Login likely successful, but check redirect location.")
        
        # Example: Follow redirect to see the target page
        # print("\\nFollowing redirect...")
        # final_response = session.get(redirect_location, headers=GET_HEADERS) # Use GET_HEADERS or POST_HEADERS
        # print(f"Final page status: {final_response.status_code}")
        # print(f"Final page URL: {final_response.url}")
        # print(f"Final page content (first 500 chars):\\n{final_response.text[:500]}")

    elif response.status_code == 200: # Sometimes errors are shown on a 200 OK page
        print("\\nResponse Content (first 1000 chars):")
        print(response.text[:1000]) # You can increase this (e.g., to 3000) if the error message is not in the first 1000 chars

        if "formRecaptcha" in response.text or "captcha" in response.text.lower():
            print("\\n[WARNING] CAPTCHA detected on page. Script cannot proceed.")
        
        # Try to find specific error messages
        specific_error_match = re.search(r'<span\\s+[^>]*class="[^"]*kc-feedback-text[^"]*"[^>]*>([^<]+)<\\/span>', response.text, re.IGNORECASE)
        
        if specific_error_match:
            error_message_from_html = specific_error_match.group(1).strip()
            print(f"\\n[ERROR] Login failed. Message from page: '{error_message_from_html}'")
        elif "invalid_grant" in response.text: # Check for "invalid_grant" specifically
             print("\\n[ERROR] Login failed: invalid_grant. This often means an issue with the session, codes, or client configuration.")
        elif "nombre de usuario o contraseña incorrectos" in response.text.lower() or "credenciales incorrectas" in response.text.lower():
             print("\\n[ERROR] Login failed: Nombre de usuario o contraseña incorrectos.")
        # Fallback if the above are not found but "error" is in the text (less reliable, but was the previous trigger)
        elif "error" in response.text.lower(): 
             print("\\n[WARNING] Login attempt resulted in a page containing the word 'error', but no specific error message structure (like kc-feedback-text or 'invalid_grant') was identified. Please review the page content manually. Status 200, but not a redirect.")
             # Consider printing more of the response text if this happens often:
             # print(f"Full response text for debugging (first 5000 chars): \\n{response.text[:5000]}")
        else:
            print("\\n[INFO] Status 200, but not a redirect and no specific error pattern detected. Check response content manually for login status or errors.")
    else:
        print("\\nResponse Content (first 1000 chars):")
        print(response.text[:1000])
        print(f"\\n[ERROR] Login failed with status code {response.status_code}. Check response content.")


    print("\\nCookies after request:")
    for cookie in session.cookies:
        print(f"  {cookie.name}: {cookie.value}")

except requests.exceptions.RequestException as e:
    print(f"[ERROR] An HTTP error occurred: {e}")
except RuntimeError as e:
    print(f"[ERROR] A script error occurred: {e}")
except Exception as e:
    print(f"[ERROR] An unexpected error occurred: {e}")
