"""
Email Handler Module - Automated CV Collection from Email
Integrates with Gmail to fetch resume attachments
"""

import imaplib
import email
from email.header import decode_header
import os
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
import logging
from typing import List, Dict, Tuple
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from database import insert_record, execute_query

load_dotenv()

logger = logging.getLogger(__name__)

# Email configuration
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")

# Storage configuration
RESUME_FOLDER = Path("uploads/resumes")
RESUME_FOLDER.mkdir(parents=True, exist_ok=True)

RESUME_EXTENSIONS = (".pdf", ".docx", ".doc")


class EmailHandler:
    """Handles automated email fetching and resume extraction"""
    
    def __init__(self):
        self.email_address = EMAIL
        self.password = PASSWORD
        self.imap_server = IMAP_SERVER
        self.mail = None
    
    def connect(self) -> bool:
        """Connect to email server"""
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            self.mail.login(self.email_address, self.password)
            logger.info(f"✅ Connected to {self.imap_server}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to email: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from email server"""
        try:
            if self.mail:
                self.mail.logout()
                logger.info("✅ Disconnected from email server")
        except Exception as e:
            logger.error(f"⚠️  Error disconnecting: {e}")
    
    def fetch_unread_emails(self) -> List[Dict]:
        """Fetch all unread emails with metadata"""
        try:
            self.mail.select("inbox")
            result, data = self.mail.search(None, "UNSEEN")
            
            if result != "OK":
                logger.error("Failed to search emails")
                return []
            
            mail_ids = data[0].split()
            logger.info(f"📧 Found {len(mail_ids)} unread emails")
            
            emails_data = []
            
            for msg_id in mail_ids:
                try:
                    result, msg_data = self.mail.fetch(msg_id, "(RFC822)")
                    if result != "OK":
                        continue
                    
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    # Extract email metadata
                    subject = self._decode_header(msg.get("Subject", ""))
                    sender = self._decode_header(msg.get("From", ""))
                    date_str = msg.get("Date", "")
                    
                    emails_data.append({
                        "msg_id": msg_id.decode(),
                        "email_obj": msg,
                        "subject": subject,
                        "sender": sender,
                        "date": date_str
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing email {msg_id}: {e}")
                    continue
            
            return emails_data
            
        except Exception as e:
            logger.error(f"❌ Error fetching emails: {e}")
            return []
    
    def _decode_header(self, header_value: str) -> str:
        """Decode email header"""
        if not header_value:
            return ""
        
        decoded_parts = decode_header(header_value)
        decoded_string = ""
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_string += part.decode(encoding or "utf-8", errors="ignore")
            else:
                decoded_string += str(part)
        
        return decoded_string
    
    def extract_attachments(self, email_msg: email.message.Message) -> List[Tuple[str, bytes]]:
        """Extract resume attachments from email"""
        attachments = []
        
        for part in email_msg.walk():
            if part.get_content_disposition() == "attachment":
                filename = part.get_filename()
                
                if not filename:
                    continue
                
                # Check if it's a resume file
                if filename.lower().endswith(RESUME_EXTENSIONS):
                    try:
                        file_data = part.get_payload(decode=True)
                        attachments.append((filename, file_data))
                        logger.info(f"📎 Found resume attachment: {filename}")
                    except Exception as e:
                        logger.error(f"Error extracting attachment {filename}: {e}")
        
        return attachments
    
    def save_attachment(self, filename: str, file_data: bytes) -> str:
        """Save attachment to disk and return path"""
        try:
            # Create unique filename to avoid collisions
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(filename)
            
            # Sanitize filename
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
            unique_filename = f"{safe_name}_{timestamp}{ext}"
            
            filepath = RESUME_FOLDER / unique_filename
            
            with open(filepath, "wb") as f:
                f.write(file_data)
            
            logger.info(f"✅ Saved: {unique_filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ Error saving attachment: {e}")
            return None
    
    def log_email_to_db(self, email_data: Dict, attachments_count: int, resumes_count: int, status: str = "processed"):
        """Log email processing to database"""
        try:
            log_data = {
                "email_id": email_data.get("msg_id"),
                "subject": email_data.get("subject", "")[:255],
                "sender": email_data.get("sender", "")[:255],
                "has_attachment": attachments_count > 0,
                "attachments_count": attachments_count,
                "resumes_extracted": resumes_count,
                "processing_status": status,
                "fetched_at": datetime.now()
            }
            
            insert_record("email_logs", log_data)
            
        except Exception as e:
            logger.error(f"Error logging email to database: {e}")
    
    def fetch_resumes(self, mark_as_read: bool = False) -> Dict[str, any]:
        """
        Main method to fetch resumes from email
        Returns summary of operation
        """
        summary = {
            "success": False,
            "emails_checked": 0,
            "resumes_found": 0,
            "resumes_saved": [],
            "errors": []
        }
        
        try:
            # Connect to email
            if not self.connect():
                summary["errors"].append("Failed to connect to email")
                return summary
            
            # Fetch unread emails
            emails = self.fetch_unread_emails()
            summary["emails_checked"] = len(emails)
            
            # Process each email
            for email_data in emails:
                try:
                    email_msg = email_data["email_obj"]
                    
                    # Extract attachments
                    attachments = self.extract_attachments(email_msg)
                    
                    resumes_in_email = 0
                    
                    # Save attachments
                    for filename, file_data in attachments:
                        filepath = self.save_attachment(filename, file_data)
                        
                        if filepath:
                            summary["resumes_saved"].append({
                                "filename": filename,
                                "filepath": filepath,
                                "sender": email_data["sender"],
                                "subject": email_data["subject"]
                            })
                            resumes_in_email += 1
                            summary["resumes_found"] += 1
                    
                    # Log to database
                    self.log_email_to_db(
                        email_data,
                        len(attachments),
                        resumes_in_email,
                        "processed"
                    )
                    
                    # Mark as read if requested
                    if mark_as_read and resumes_in_email > 0:
                        try:
                            self.mail.store(email_data["msg_id"].encode(), '+FLAGS', '\\Seen')
                        except:
                            pass
                    
                except Exception as e:
                    logger.error(f"Error processing email: {e}")
                    summary["errors"].append(str(e))
            
            summary["success"] = True
            logger.info(f"✅ Email fetch complete: {summary['resumes_found']} resumes found")
            
        except Exception as e:
            logger.error(f"❌ Error in fetch_resumes: {e}")
            summary["errors"].append(str(e))
        
        finally:
            self.disconnect()
        
        return summary


def fetch_resumes_from_email() -> Dict:
    """Convenience function to fetch resumes"""
    handler = EmailHandler()
    return handler.fetch_resumes()


if __name__ == "__main__":
    # Test the email handler
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 Testing Email Handler...")
    result = fetch_resumes_from_email()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Success: {result['success']}")
    print(f"Emails Checked: {result['emails_checked']}")
    print(f"Resumes Found: {result['resumes_found']}")
    print(f"Resumes Saved: {len(result['resumes_saved'])}")
    
    if result['resumes_saved']:
        print("\nSaved Files:")
        for resume in result['resumes_saved']:
            print(f"  - {resume['filename']} (from {resume['sender']})")
    
    if result['errors']:
        print(f"\nErrors: {len(result['errors'])}")
        for error in result['errors']:
            print(f"  - {error}")
