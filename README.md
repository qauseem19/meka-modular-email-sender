# Email API with FastAPI

A robust FastAPI application for sending emails via SMTP with comprehensive error handling and support for attachments.

## Features

- ✅ Send emails via SMTP with custom credentials
- ✅ Support for HTML and plain text emails
- ✅ CC and BCC recipients
- ✅ File attachments (Base64 encoded)
- ✅ Comprehensive error handling
- ✅ CORS enabled for web applications
- ✅ Structured JSON response format
- ✅ Health check endpoints
- ✅ Automatic SMTP connection management

## Installation

1. **Clone or download the project files**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   
   Copy the example environment file:
   ```bash
   copy env.example .env
   ```
   
   Edit the `.env` file with your SMTP credentials:
   ```env
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USE_TLS=true
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   ```

4. **Run the application:**
   ```bash
   python main.py
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## API Endpoints

### 1. Health Check
- **GET** `/health`
- Returns the health status of the service

### 2. Send Email
- **POST** `/send-email`
- Sends an email via SMTP

## Request Format

All responses follow this JSON structure [[memory:4977149]]:
```json
{
  "version": "1.0.0.0",
  "statusCode": 200,
  "message": "Successful",
  "isError": null,
  "responseException": null,
  "result": { ... }
}
```

### Send Email Request Example

```json
{
  "to_email": "recipient@example.com",
  "subject": "Test Email",
  "body": "<h1>Hello World!</h1><p>This is a test email.</p>",
  "body_type": "html",
  "from_name": "Your Name",
  "reply_to": "noreply@yourcompany.com",
  "cc": ["cc@example.com"],
  "bcc": ["bcc@example.com"],
  "attachments": [
    {
      "filename": "document.pdf",
      "content": "base64_encoded_content_here",
      "content_type": "application/pdf"
    }
  ]
}
```

**Note:** SMTP credentials are now loaded from environment variables (`.env` file) for security.

### Response Example

**Success:**
```json
{
  "version": "1.0.0.0",
  "statusCode": 200,
  "message": "Email sent successfully",
  "isError": null,
  "responseException": null,
  "result": {
    "emailId": "recipient@example.com",
    "subject": "Test Email",
    "timestamp": "2024-01-15T10:30:00.000000",
    "status": "sent",
    "recipients": {
      "to": "recipient@example.com",
      "cc": ["cc@example.com"],
      "bcc": ["bcc@example.com"]
    }
  }
}
```

**Error:**
```json
{
  "version": "1.0.0.0",
  "statusCode": 401,
  "message": "Failed to send email",
  "isError": true,
  "responseException": "SMTP Authentication failed: Invalid credentials",
  "result": null
}
```

## Environment Variables Configuration

Create a `.env` file in the project root with the following variables:

### Required Variables
```env
SMTP_SERVER=your-smtp-server.com
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-password
```

### Optional Variables
```env
SMTP_USE_TLS=true  # Default: true
```

### Configuration Examples

#### Gmail
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

#### Outlook/Hotmail
```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
```

#### Yahoo
```env
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@yahoo.com
SMTP_PASSWORD=your-app-password
```

#### Custom SMTP Server
```env
SMTP_SERVER=your-smtp-server.com
SMTP_PORT=25
SMTP_USE_TLS=false
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password
```

## Testing with cURL

```bash
curl -X POST "http://localhost:8000/send-email" \
  -H "Content-Type: application/json" \
  -d '{
    "to_email": "test@example.com",
    "subject": "Test Email",
    "body": "Hello from FastAPI Email Service!",
    "body_type": "plain"
  }'
```

**Note:** Make sure your `.env` file is configured with the correct SMTP credentials before testing.

## Error Handling

The API handles various error scenarios:

- **401**: SMTP Authentication failed
- **400**: Invalid recipient email address
- **503**: SMTP Server connection issues
- **500**: Internal server errors

## Security Notes

1. **Use App Passwords**: For Gmail and other providers, use app-specific passwords instead of your main password
2. **Environment Variables**: SMTP credentials are stored in environment variables for security
3. **HTTPS**: Use HTTPS in production environments
4. **Rate Limiting**: Consider implementing rate limiting for production use
5. **Never Commit .env**: Add `.env` to your `.gitignore` file to avoid committing credentials

## Production Deployment

For production deployment:

1. **Environment Variables**: Set SMTP credentials as system environment variables or use a secure secrets manager
2. **HTTPS**: Use a reverse proxy like Nginx with SSL certificates
3. **Logging**: Configure proper logging levels
4. **Monitoring**: Add health checks and monitoring
5. **Rate Limiting**: Implement rate limiting middleware
6. **Docker**: Consider containerizing the application for easier deployment

## License

This project is open source and available under the MIT License.
