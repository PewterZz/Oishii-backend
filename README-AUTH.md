# Oishii Authentication Setup

This document provides instructions on how to set up Supabase authentication for the Oishii backend.

## Supabase Configuration

1. Go to your Supabase project dashboard: https://app.supabase.com/
2. Navigate to Authentication > URL Configuration
3. Set the Site URL to your backend URL (e.g., `https://oishii-backend.fly.dev` or `http://localhost:8000`)
4. Add the following redirect URLs:
   - `https://oishii-backend.fly.dev/api/v1/auth/callback`
   - `http://localhost:8000/api/v1/auth/callback`
5. Save the changes

## Environment Variables

Make sure the following environment variables are set in your `.env` file:

```
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-anon-key
API_URL=https://oishii-backend.fly.dev  # or http://localhost:8000 for local development
FRONTEND_URL=http://localhost:3000  # Will be updated when frontend is ready
```

## Testing Authentication

Since there's no frontend yet, you can test authentication using the built-in Auth Test UI:

1. Start the backend server
2. Visit `http://localhost:8000/api/v1/auth/` or `https://oishii-backend.fly.dev/api/v1/auth/`
3. Click on "Test Auth UI"
4. Use the UI to register, verify, and log in

## Authentication Flow

1. **Registration**:
   - User registers with email, password, and name
   - Supabase sends a verification email
   - User data is stored in the database with `is_verified` set to `false`

2. **Email Verification**:
   - User clicks the verification link in the email
   - The link redirects to `/api/v1/auth/callback` with `token_hash` and `type` parameters
   - The backend verifies the token with Supabase
   - If successful, the user's `is_verified` status is updated to `true`

3. **Login**:
   - User logs in with email and password
   - The backend verifies credentials with Supabase
   - If successful, the backend returns access and refresh tokens

## API Endpoints

### Registration
```
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "password": "password123",
  "name": "User Name"
}
```

### Login
```
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "password123"
}
```

### Check Verification Status
```
GET /api/v1/auth/check-verification/{email}
```

### Resend Confirmation Email
```
POST /api/v1/auth/resend-confirmation
{
  "email": "user@example.com"
}
```

### Manual Verification (For Testing)
```
POST /api/v1/auth/manual-verify/{email}
```

## Troubleshooting

If email verification isn't working:

1. Check the Supabase dashboard for any email delivery issues
2. Verify that the redirect URLs are correctly configured
3. Check the backend logs for any errors during the verification process
4. Use the "Debug Settings" button in the Auth Test UI to check your configuration
5. Try manually verifying the user for testing purposes

## When Frontend is Ready

When the frontend is ready, update the `FRONTEND_URL` environment variable and modify the authentication flow to:

1. Redirect users to the frontend after email verification
2. Handle authentication tokens on the frontend
3. Implement proper session management

## Security Considerations

- The current implementation stores user data in both Supabase Auth and your database
- Access tokens should be stored securely and included in the Authorization header for API requests
- Consider implementing token refresh logic to maintain user sessions
- Add rate limiting to prevent brute force attacks on login endpoints 