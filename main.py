from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
from datetime import datetime
import os
from dotenv import load_dotenv
import requests
import mimetypes
from urllib.parse import urlparse
import tempfile

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Email API",
    description="API for sending emails via SMTP",
    version="1.0.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SendEmailRequest(BaseModel):
    to_email: EmailStr
    subject: str
    body: str
    body_type: str = "html"  # "html" or "plain"
    from_name: Optional[str] = None
    reply_to: Optional[EmailStr] = None
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None
    attachments: Optional[List[str]] = None

class ApiResponse(BaseModel):
    version: str = "1.0.0.0"
    statusCode: int
    message: str
    isError: Optional[bool] = None
    responseException: Optional[str] = None
    result: Optional[dict] = None

# Helper function to download file from URL
def download_file_from_url(url: str, max_size_mb: int = 10) -> tuple[bytes, str, str]:
    """
    Download file from URL and return content, filename, and content type
    
    Args:
        url: URL to download the file from
        max_size_mb: Maximum file size in MB (default: 10MB)
    
    Returns:
        tuple: (file_content, filename, content_type)
    
    Raises:
        HTTPException: If download fails or file is too large
    """
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid URL format: {url}"
            )
        
        # Download file with timeout and size limit
        max_size_bytes = max_size_mb * 1024 * 1024
        
        response = requests.get(
            url, 
            timeout=30, 
            stream=True,
            headers={'User-Agent': 'FastAPI-Email-Service/1.0'}
        )
        response.raise_for_status()
        
        # Check content length if available
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > max_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size allowed: {max_size_mb}MB"
            )
        
        # Download content
        content = b""
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > max_size_bytes:
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Maximum size allowed: {max_size_mb}MB"
                )
        
        # Extract filename from URL or Content-Disposition header
        filename = None
        
        # Try to get filename from Content-Disposition header
        content_disposition = response.headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"\'')
        
        # If no filename in header, extract from URL
        if not filename:
            filename = os.path.basename(parsed_url.path)
            if not filename or filename == '/':
                filename = 'attachment'
        
        # Detect content type
        content_type = response.headers.get('content-type', 'application/octet-stream')
        if content_type == 'application/octet-stream':
            # Try to guess from filename
            guessed_type, _ = mimetypes.guess_type(filename)
            if guessed_type:
                content_type = guessed_type
        
        return content, filename, content_type
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download file from URL {url}: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to download file from URL: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error downloading file from URL {url}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing attachment URL: {str(e)}"
        )

# Email Service
class EmailService:
    def __init__(self):
        self.smtp_connection = None
        # Load SMTP credentials from environment variables
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.username = os.getenv("SMTP_USERNAME")
        self.password = os.getenv("SMTP_PASSWORD")
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        
        # Validate required environment variables
        if not all([self.smtp_server, self.username, self.password]):
            raise ValueError("Missing required SMTP environment variables. Please check SMTP_SERVER, SMTP_USERNAME, and SMTP_PASSWORD.")
    
    async def send_email(self, request: SendEmailRequest) -> dict:
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{request.from_name or self.username} <{self.username}>"
            msg['To'] = request.to_email
            msg['Subject'] = request.subject
            
            if request.reply_to:
                msg['Reply-To'] = request.reply_to
            
            if request.cc:
                msg['Cc'] = ', '.join(request.cc)
            
            if request.bcc:
                msg['Bcc'] = ', '.join(request.bcc)
            
            # Add body
            if request.body_type.lower() == "html":
                msg.attach(MIMEText(request.body, 'html'))
            else:
                msg.attach(MIMEText(request.body, 'plain'))
            
            # Add attachments if any
            if request.attachments:
                for attachment in request.attachments:
                    try:
                        # Download file from URL
                        file_content, filename, content_type = download_file_from_url(attachment)
                        
                        # Create attachment part
                        main_type, sub_type = content_type.split('/', 1) if '/' in content_type else ('application', 'octet-stream')
                        part = MIMEBase(main_type, sub_type)
                        part.set_payload(file_content)
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename="{filename}"'
                        )
                        msg.attach(part)
                        
                        logger.info(f"Successfully attached file: {filename} from URL: {attachment}")
                        
                    except Exception as e:
                        logger.error(f"Failed to process attachment from URL {attachment}: {str(e)}")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Failed to process attachment from URL {attachment}: {str(e)}"
                        )
            
            # Connect to SMTP server
            self.smtp_connection = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            if self.use_tls:
                self.smtp_connection.starttls()
            
            # Login
            self.smtp_connection.login(self.username, self.password)
            
            # Prepare recipients
            recipients = [request.to_email]
            if request.cc:
                recipients.extend(request.cc)
            if request.bcc:
                recipients.extend(request.bcc)
            
            # Send email
            text = msg.as_string()
            self.smtp_connection.sendmail(self.username, recipients, text)
            
            # Close connection
            self.smtp_connection.quit()
            
            logger.info(f"Email sent successfully to {request.to_email}")
            
            return {
                "emailId": request.to_email,
                "subject": request.subject,
                "timestamp": datetime.now().isoformat(),
                "status": "sent",
                "recipients": {
                    "to": request.to_email,
                    "cc": request.cc or [],
                    "bcc": request.bcc or []
                }
            }
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail=f"SMTP Authentication failed: {str(e)}"
            )
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"Recipients refused: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid recipient email address: {str(e)}"
            )
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP Server disconnected: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"SMTP Server connection lost: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send email: {str(e)}"
            )
        finally:
            if self.smtp_connection:
                try:
                    self.smtp_connection.quit()
                except:
                    pass

# Initialize email service
try:
    email_service = EmailService()
except ValueError as e:
    logger.error(f"Failed to initialize email service: {str(e)}")
    email_service = None

@app.get("/")
async def root():
    """Health check endpoint"""
    return ApiResponse(
        statusCode=200,
        message="Email API is running",
        result={"service": "Email API", "version": "1.0.0.0"}
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return ApiResponse(
        statusCode=200,
        message="Service is healthy",
        result={"status": "healthy", "timestamp": datetime.now().isoformat()}
    )

@app.post("/send-email", response_model=ApiResponse)
async def send_email(request: SendEmailRequest):
    """
    Send an email via SMTP
    
    - **to_email**: Recipient email address
    - **subject**: Email subject
    - **body**: Email body content
    - **body_type**: Type of body content ("html" or "plain")
    - **from_name**: Optional sender name
    - **reply_to**: Optional reply-to email address
    - **cc**: Optional CC recipients
    - **bcc**: Optional BCC recipients
    - **attachments**: Optional file attachments (URL-based download)
    
    Note: SMTP credentials are loaded from environment variables
    """
    try:
        if email_service is None:
            raise HTTPException(
                status_code=500,
                detail="Email service not initialized. Please check environment variables."
            )
        
        result = await email_service.send_email(request)
        
        return ApiResponse(
            statusCode=200,
            message="Email sent successfully",
            result=result
        )
        
    except HTTPException as e:
        return ApiResponse(
            statusCode=e.status_code,
            message="Failed to send email",
            isError=True,
            responseException=e.detail,
            result=None
        )
    except Exception as e:
        logger.error(f"Unexpected error in send_email endpoint: {str(e)}")
        return ApiResponse(
            statusCode=500,
            message="Internal server error",
            isError=True,
            responseException=str(e),
            result=None
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
