import requests
import json
import os
from datetime import datetime
from typing import Optional

class BrevoEmailService:
    def __init__(self, api_key: str = None, sender_email: str = None, sender_name: str = None):
        """
        Initialize Brevo email service
        
        Args:
            api_key: Brevo API key. If not provided, will try to get from environment variable BREVO_API_KEY
            sender_email: Sender email address. If not provided, will use BREVO_SENDER_EMAIL env var
            sender_name: Sender name. If not provided, will use BREVO_SENDER_NAME env var
        """
        print(os.getenv('BREVO_API_KEY'))
        self.api_key = os.getenv('BREVO_API_KEY')
        if not self.api_key:
            raise ValueError("Brevo API key is required. Set BREVO_API_KEY environment variable or pass api_key parameter.")
        
        self.sender_email = sender_email or os.getenv('BREVO_SENDER_EMAIL', 'noreply@abzhardware.com')
        self.sender_name = sender_name or os.getenv('BREVO_SENDER_NAME', 'ABZ Hardware')
        
        self.base_url = "https://api.brevo.com/v3"
        self.headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'api-key': self.api_key
        }
    
    def send_password_reset_email(self, to_email: str, reset_url: str, user_name: str) -> dict:
        """
        Send password reset email using Brevo API
        
        Args:
            to_email: Recipient email address
            reset_url: Password reset URL
            user_name: User's name for personalization
            
        Returns:
            dict: API response
        """
        email_data = {
            "sender": {
                "name": self.sender_name,
                "email": self.sender_email
            },
            "to": [
                {
                    "email": to_email,
                    "name": user_name
                }
            ],
            "subject": "Password Reset Request - ABZ Sales Portal",
            "htmlContent": self._get_password_reset_html(reset_url, user_name),
            "textContent": self._get_password_reset_text(reset_url, user_name)
        }
        
        return self._send_email(email_data)
    
    def send_welcome_email(self, to_email: str, user_name: str, login_url: str) -> dict:
        """
        Send welcome email to new users
        
        Args:
            to_email: Recipient email address
            user_name: User's name
            login_url: Login URL
            
        Returns:
            dict: API response
        """
        email_data = {
            "sender": {
                "name": self.sender_name,
                "email": self.sender_email
            },
            "to": [
                {
                    "email": to_email,
                    "name": user_name
                }
            ],
            "subject": "Welcome to ABZ Sales Portal",
            "htmlContent": self._get_welcome_html(user_name, login_url),
            "textContent": self._get_welcome_text(user_name, login_url)
        }
        
        return self._send_email(email_data)
    
    def send_password_change_alert(self, to_email: str, user_name: str, change_time: str) -> dict:
        """
        Send password change alert email
        
        Args:
            to_email: Recipient email address
            user_name: User's name
            change_time: Time when password was changed
            
        Returns:
            dict: API response
        """
        email_data = {
            "sender": {
                "name": self.sender_name,
                "email": self.sender_email
            },
            "to": [
                {
                    "email": to_email,
                    "name": user_name
                }
            ],
            "subject": "Password Changed - ABZ Sales Portal",
            "htmlContent": self._get_password_change_alert_html(user_name, change_time),
            "textContent": self._get_password_change_alert_text(user_name, change_time)
        }
        
        return self._send_email(email_data)
    
    def send_invoice_email(self, to_email: str, user_name: str, order_id: int, invoice_number: str, pdf_attachment: bytes = None) -> dict:
        """
        Send invoice email with PDF attachment
        
        Args:
            to_email: Recipient email address
            user_name: User's name
            order_id: Order ID
            invoice_number: Invoice number
            pdf_attachment: PDF file as bytes
            
        Returns:
            dict: API response
        """
        email_data = {
            "sender": {
                "name": self.sender_name,
                "email": self.sender_email
            },
            "to": [
                {
                    "email": to_email,
                    "name": user_name
                }
            ],
            "subject": f"Invoice #{invoice_number} - Order #{order_id} - ABZ Hardware",
            "htmlContent": self._get_invoice_email_html(user_name, order_id, invoice_number),
            "textContent": self._get_invoice_email_text(user_name, order_id, invoice_number)
        }
        
        # Add attachment if provided
        if pdf_attachment:
            import base64
            email_data["attachment"] = [
                {
                    "name": f"invoice_{invoice_number}.pdf",
                    "content": base64.b64encode(pdf_attachment).decode('utf-8')
                }
            ]
        
        return self._send_email(email_data)
    
    def send_receipt_email(self, to_email: str, user_name: str, order_id: int, receipt_number: str, payment_amount: float, pdf_attachment: bytes = None) -> dict:
        """
        Send receipt email with PDF attachment
        
        Args:
            to_email: Recipient email address
            user_name: User's name
            order_id: Order ID
            receipt_number: Receipt number
            payment_amount: Payment amount
            pdf_attachment: PDF file as bytes
            
        Returns:
            dict: API response
        """
        email_data = {
            "sender": {
                "name": self.sender_name,
                "email": self.sender_email
            },
            "to": [
                {
                    "email": to_email,
                    "name": user_name
                }
            ],
            "subject": f"Receipt #{receipt_number} - Order #{order_id} - ABZ Hardware",
            "htmlContent": self._get_receipt_email_html(user_name, order_id, receipt_number, payment_amount),
            "textContent": self._get_receipt_email_text(user_name, order_id, receipt_number, payment_amount)
        }
        
        # Add attachment if provided
        if pdf_attachment:
            import base64
            email_data["attachment"] = [
                {
                    "name": f"receipt_{receipt_number}.pdf",
                    "content": base64.b64encode(pdf_attachment).decode('utf-8')
                }
            ]
        
        return self._send_email(email_data)
    
    def _send_email(self, email_data: dict) -> dict:
        """
        Send email using Brevo API
        
        Args:
            email_data: Email data dictionary
            
        Returns:
            dict: API response
        """
        try:
            response = requests.post(
                f"{self.base_url}/smtp/email",
                headers=self.headers,
                data=json.dumps(email_data)
            )
            
            if response.status_code == 201:
                return {
                    'success': True,
                    'message_id': response.json().get('messageId'),
                    'message': 'Email sent successfully'
                }
            else:
                return {
                    'success': False,
                    'error': f"Failed to send email. Status: {response.status_code}, Response: {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Exception occurred while sending email: {str(e)}"
            }
    
    def _get_password_reset_html(self, reset_url: str, user_name: str) -> str:
        """Generate HTML content for password reset email"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Password Reset - ABZ Sales Portal</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #666;
                    font-size: 12px;
                }}
                .warning {{
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>ABZ Hardware</h1>
                <p>Sales Portal - Password Reset</p>
            </div>
            
            <div class="content">
                <h2>Hello {user_name},</h2>
                
                <p>We received a request to reset your password for the ABZ Sales Portal. If you didn't make this request, you can safely ignore this email.</p>
                
                <div style="text-align: center;">
                    <a href="{reset_url}" class="button">Reset Password</a>
                </div>
                
                <div class="warning">
                    <strong>Important:</strong> This link will expire in 24 hours for security reasons.
                </div>
                
                <p>If the button above doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #667eea;">{reset_url}</p>
                
                <p>If you have any questions or need assistance, please contact your system administrator.</p>
                
                <p>Best regards,<br>
                ABZ Hardware Team</p>
            </div>
            
            <div class="footer">
                <p>This email was sent from the ABZ Sales Portal. Please do not reply to this email.</p>
                <p>&copy; {datetime.now().year} ABZ Hardware. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
    
    def _get_password_reset_text(self, reset_url: str, user_name: str) -> str:
        """Generate plain text content for password reset email"""
        return f"""
        Password Reset Request - ABZ Sales Portal
        
        Hello {user_name},
        
        We received a request to reset your password for the ABZ Sales Portal. If you didn't make this request, you can safely ignore this email.
        
        To reset your password, please click the following link:
        {reset_url}
        
        Important: This link will expire in 24 hours for security reasons.
        
        If you have any questions or need assistance, please contact your system administrator.
        
        Best regards,
        ABZ Hardware Team
        
        ---
        This email was sent from the ABZ Sales Portal. Please do not reply to this email.
        © {datetime.now().year} ABZ Hardware. All rights reserved.
        """
    
    def _get_welcome_html(self, user_name: str, login_url: str) -> str:
        """Generate HTML content for welcome email"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Welcome to ABZ Sales Portal</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>ABZ Hardware</h1>
                <p>Sales Portal - Welcome</p>
            </div>
            
            <div class="content">
                <h2>Welcome {user_name}!</h2>
                
                <p>Welcome to the ABZ Sales Portal! Your account has been successfully created and you can now access the sales management system.</p>
                
                <div style="text-align: center;">
                    <a href="{login_url}" class="button">Login to Portal</a>
                </div>
                
                <p>With the ABZ Sales Portal, you can:</p>
                <ul>
                    <li>Create and manage orders</li>
                    <li>Track inventory and stock levels</li>
                    <li>Process payments and generate invoices</li>
                    <li>View sales reports and analytics</li>
                </ul>
                
                <p>If you have any questions or need assistance, please contact your system administrator.</p>
                
                <p>Best regards,<br>
                ABZ Hardware Team</p>
            </div>
            
            <div class="footer">
                <p>This email was sent from the ABZ Sales Portal. Please do not reply to this email.</p>
                <p>&copy; {datetime.now().year} ABZ Hardware. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
    
    def _get_welcome_text(self, user_name: str, login_url: str) -> str:
        """Generate plain text content for welcome email"""
        return f"""
        Welcome to ABZ Sales Portal
        
        Hello {user_name},
        
        Welcome to the ABZ Sales Portal! Your account has been successfully created and you can now access the sales management system.
        
        Login to your account: {login_url}
        
        With the ABZ Sales Portal, you can:
        - Create and manage orders
        - Track inventory and stock levels
        - Process payments and generate invoices
        - View sales reports and analytics
        
        If you have any questions or need assistance, please contact your system administrator.
        
        Best regards,
        ABZ Hardware Team
        
        ---
        This email was sent from the ABZ Sales Portal. Please do not reply to this email.
        © {datetime.now().year} ABZ Hardware. All rights reserved.
        """
    
    def _get_password_change_alert_html(self, user_name: str, change_time: str) -> str:
        """Generate HTML content for password change alert email"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Password Changed - ABZ Sales Portal</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .alert-box {{
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .info-box {{
                    background: #d1ecf1;
                    border: 1px solid #bee5eb;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>ABZ Hardware</h1>
                <p>Sales Portal - Security Alert</p>
            </div>
            
            <div class="content">
                <h2>Hello {user_name},</h2>
                
                <div class="alert-box">
                    <h3>🔒 Password Changed Successfully</h3>
                    <p>Your password for the ABZ Sales Portal has been successfully changed.</p>
                </div>
                
                <div class="info-box">
                    <strong>Change Details:</strong><br>
                    • Time: {change_time}<br>
                    • Account: ABZ Sales Portal<br>
                    • Action: Password Reset
                </div>
                
                <p>If you did not request this password change, please contact your system administrator immediately as your account may have been compromised.</p>
                
                <p>For security reasons, we recommend:</p>
                <ul>
                    <li>Using a strong, unique password</li>
                    <li>Not sharing your password with anyone</li>
                    <li>Logging out when using shared computers</li>
                    <li>Regularly updating your password</li>
                </ul>
                
                <p>If you have any questions or need assistance, please contact your system administrator.</p>
                
                <p>Best regards,<br>
                ABZ Hardware Team</p>
            </div>
            
            <div class="footer">
                <p>This email was sent from the ABZ Sales Portal. Please do not reply to this email.</p>
                <p>&copy; {datetime.now().year} ABZ Hardware. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
    
    def _get_password_change_alert_text(self, user_name: str, change_time: str) -> str:
        """Generate text content for password change alert email"""
        return f"""
Dear {user_name},

Your password for the ABZ Sales Portal has been changed successfully.

Change Time: {change_time}

If you did not make this change, please contact your system administrator immediately.

Best regards,
ABZ Hardware Team
        """.strip()
    
    def _get_invoice_email_html(self, user_name: str, order_id: int, invoice_number: str) -> str:
        """Generate HTML content for invoice email"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Invoice #{invoice_number}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #007bff;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 0 0 5px 5px;
        }}
        .invoice-info {{
            background-color: white;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
            border-left: 4px solid #007bff;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
        }}
        .btn {{
            display: inline-block;
            padding: 10px 20px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 10px 5px;
        }}
        .btn:hover {{
            background-color: #0056b3;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>ABZ Hardware</h1>
        <p>Your Invoice is Ready</p>
    </div>
    
    <div class="content">
        <p>Dear {user_name},</p>
        
        <p>Your invoice for Order #{order_id} has been generated and is attached to this email.</p>
        
        <div class="invoice-info">
            <h3>Invoice Details</h3>
            <p><strong>Invoice Number:</strong> {invoice_number}</p>
            <p><strong>Order Number:</strong> #{order_id}</p>
            <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
        </div>
        
        <p>Please find your invoice attached to this email. You can also view and download it from your account.</p>
        
        <p>If you have any questions about this invoice, please don't hesitate to contact us.</p>
        
        <p>Thank you for choosing ABZ Hardware!</p>
        
        <div class="footer">
            <p><strong>ABZ Hardware</strong></p>
            <p>Your trusted partner for quality hardware solutions</p>
        </div>
    </div>
</body>
</html>
        """.strip()
    
    def _get_invoice_email_text(self, user_name: str, order_id: int, invoice_number: str) -> str:
        """Generate text content for invoice email"""
        return f"""
Dear {user_name},

Your invoice for Order #{order_id} has been generated and is attached to this email.

Invoice Details:
- Invoice Number: {invoice_number}
- Order Number: #{order_id}
- Date: {datetime.now().strftime('%B %d, %Y')}

Please find your invoice attached to this email. You can also view and download it from your account.

If you have any questions about this invoice, please don't hesitate to contact us.

Thank you for choosing ABZ Hardware!

Best regards,
ABZ Hardware Team
        """.strip()

    def _get_receipt_email_html(self, user_name: str, order_id: int, receipt_number: str, payment_amount: float) -> str:
        """Generate HTML content for receipt email"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Receipt #{receipt_number}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #28a745;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 0 0 5px 5px;
        }}
        .receipt-info {{
            background-color: white;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
            border-left: 4px solid #28a745;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
        }}
        .btn {{
            display: inline-block;
            padding: 10px 20px;
            background-color: #28a745;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 10px 5px;
        }}
        .btn:hover {{
            background-color: #218838;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>ABZ Hardware</h1>
        <p>Your Receipt is Ready</p>
    </div>
    
    <div class="content">
        <p>Dear {user_name},</p>
        
        <p>Your receipt for Order #{order_id} has been generated and is attached to this email.</p>
        
        <div class="receipt-info">
            <h3>Receipt Details</h3>
            <p><strong>Receipt Number:</strong> {receipt_number}</p>
            <p><strong>Order Number:</strong> #{order_id}</p>
            <p><strong>Payment Amount:</strong> KSh{payment_amount:.2f}</p>
            <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
        </div>
        
        <p>Please find your receipt attached to this email. You can also view and download it from your account.</p>
        
        <p>If you have any questions about this receipt, please don't hesitate to contact us.</p>
        
        <p>Thank you for choosing ABZ Hardware!</p>
        
        <div class="footer">
            <p><strong>ABZ Hardware</strong></p>
            <p>Your trusted partner for quality hardware solutions</p>
        </div>
    </div>
</body>
</html>
        """.strip()

    def _get_receipt_email_text(self, user_name: str, order_id: int, receipt_number: str, payment_amount: float) -> str:
        """Generate text content for receipt email"""
        return f"""
Dear {user_name},

Your receipt for Order #{order_id} has been generated and is attached to this email.

Receipt Details:
- Receipt Number: {receipt_number}
- Order Number: #{order_id}
- Payment Amount: KSh{payment_amount:.2f}
- Date: {datetime.now().strftime('%B %d, %Y')}

Please find your receipt attached to this email. You can also view and download it from your account.

If you have any questions about this receipt, please don't hesitate to contact us.

Thank you for choosing ABZ Hardware!

Best regards,
ABZ Hardware Team
        """.strip()

# Global email service instance
email_service = None

def init_email_service(api_key: str = None):
    """Initialize the global email service"""
    global email_service
    try:
        email_service = BrevoEmailService(api_key)
        print("✅ Email service initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize email service: {str(e)}")
        email_service = None

def get_email_service() -> Optional[BrevoEmailService]:
    """Get the global email service instance"""
    return email_service 