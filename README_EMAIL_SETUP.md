# Email Setup Instructions for ABZ Sales Portal

## Brevo Email Integration Setup

This guide will help you set up Brevo (formerly Sendinblue) email service for the ABZ Sales Portal.

### 1. Get Brevo API Key

1. Go to [Brevo](https://www.brevo.com/) and create an account
2. Navigate to your dashboard
3. Go to **Settings** → **API Keys**
4. Create a new API key with the following permissions:
   - **SMTP** (for sending emails)
5. Copy the API key

### 2. Environment Configuration

Create a `.env` file in the root directory with the following content:

```env
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-super-secret-key-change-this-in-production

# Database Configuration
DATABASE_URL=postgresql://postgres:deno0707@localhost:5432/abz

# Brevo Email Configuration
BREVO_API_KEY=your-brevo-api-key-here
BREVO_SENDER_EMAIL=noreply@abzhardware.com
BREVO_SENDER_NAME=ABZ Hardware

# Application Configuration
APP_URL=http://localhost:5000
```

### 3. Verify Sender Email

1. In your Brevo dashboard, go to **Settings** → **Senders & IP**
2. Add and verify your sender email address (e.g., `noreply@abzhardware.com`)
3. Follow the verification process (check your email and click the verification link)

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Test Email Functionality

1. Start the application:
   ```bash
   python main.py
   ```

2. Go to the login page and click "Forgot Password"
3. Enter a valid sales staff email address
4. Check if the email is sent successfully

### 6. Email Templates

The application includes the following email templates:

- **Password Reset Email**: Sent when users request password reset
- **Welcome Email**: Can be sent to new users (ready for future use)

### 7. Troubleshooting

#### Email Not Sending
- Check if your Brevo API key is correct
- Verify your sender email is verified in Brevo
- Check the application logs for error messages
- Ensure your Brevo account has sufficient credits

#### API Key Issues
- Make sure the API key has SMTP permissions
- Check if the API key is properly set in the `.env` file
- Restart the application after updating the `.env` file

#### Sender Email Issues
- The sender email must be verified in Brevo
- Update the `BREVO_SENDER_EMAIL` in your `.env` file to match the verified email

### 8. Production Deployment

For production deployment:

1. Set `FLASK_ENV=production` in your environment
2. Use a strong, unique `SECRET_KEY`
3. Update `APP_URL` to your production domain
4. Ensure your Brevo account has sufficient sending capacity
5. Monitor email delivery rates and bounces

### 9. Email Features

- **Password Reset**: Secure token-based password reset with 24-hour expiration
- **Professional Templates**: HTML and plain text versions
- **Error Handling**: Graceful fallback if email service is unavailable
- **Security**: Tokens are single-use and expire automatically

### 10. Customization

You can customize email templates by editing the methods in `email_service.py`:
- `_get_password_reset_html()` - HTML version of password reset email
- `_get_password_reset_text()` - Plain text version of password reset email
- `_get_welcome_html()` - HTML version of welcome email
- `_get_welcome_text()` - Plain text version of welcome email

### Support

If you encounter any issues with the email setup, please check:
1. Brevo documentation: https://developers.brevo.com/
2. Application logs for error messages
3. Brevo dashboard for delivery status 