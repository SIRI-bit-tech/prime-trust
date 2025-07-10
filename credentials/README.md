# Gmail API Setup for PrimeTrust Banking

This directory contains the Gmail API credentials needed for production email delivery.

## Required Files

### 1. `gmail-oauth.json` (OAuth2 Credentials)
Download this file from Google Cloud Console:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project: "primetrust-banking"
3. Navigate to APIs & Services > Credentials
4. Find your OAuth 2.0 Client ID: "PrimeTrust Banking Email Client"
5. Click the download icon to get the JSON file
6. Rename it to `gmail-oauth.json` and place it in this directory

### 2. `token.json` (Auto-generated)
This file will be created automatically during the first OAuth flow. You don't need to create it manually.

## Environment Variables

Add these to your `.env` file:

```bash
# Gmail API Configuration
GMAIL_SENDER_EMAIL=your-gmail@gmail.com
GMAIL_OAUTH_CREDENTIALS_FILE=credentials/gmail-oauth.json
GMAIL_TOKEN_FILE=credentials/token.json
GMAIL_SUBJECT_PREFIX=[PrimeTrust] 
```

## First-Time Setup

1. Place your `gmail-oauth.json` file in this directory
2. Set the environment variables in your `.env` file
3. Run the test command: `python manage.py test_gmail --test-email your-email@example.com`
4. Follow the OAuth flow in your browser when prompted
5. The `token.json` file will be created automatically

## Testing

Test the Gmail API setup:

```bash
# Check configuration only
python manage.py test_gmail --check-only

# Send a test email
python manage.py test_gmail --test-email your-email@example.com
```

## Production Deployment

For production servers:
1. Complete the OAuth flow on a local machine first
2. Copy both `gmail-oauth.json` and `token.json` to the production server
3. Ensure the service account has proper permissions
4. Monitor the logs for any authentication issues

## Security Notes

- Keep these files secure and never commit them to version control
- The `.gitignore` file should exclude this entire directory
- Use environment variables for sensitive configuration
- Regularly rotate your OAuth credentials for security 