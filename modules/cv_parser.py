"""
CV Parser Module - AI-Based CV Parsing & Data Extraction
Combines PDF/DOCX extraction, OCR, and LLM-based structured parsing
Integrates code from existing PDF_to_DB module and rms_app.py
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from pdfminer.high_level import extract_text as pdf_extract_text
from docx import Document
import pdfplumber
import spacy
import re
import json
import logging
from typing import Dict, Optional
from groq import Groq
import os
from dotenv import load_dotenv
import unicodedata

# Try importing OCR libraries
try:
    from pdf2image import convert_from_bytes
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

load_dotenv()

logger = logging.getLogger(__name__)

# Load Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Load Spacy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("Spacy model not found. Some NER features will be limited.")
    nlp = None


# LLM System Prompt for Resume Parsing
SYSTEM_PROMPT = """You are a resume parsing engine.

HARD FAILURE RULE (MANDATORY):
- EVERY value MUST be either a SINGLE STRING or null.
- ARRAYS ([]) are FORBIDDEN.
- OBJECTS ({}) are FORBIDDEN.
- If data is structured, FLATTEN it into text.
- If unsure, SIMPLIFY.

INPUT:
- Resume text from PDF or OCR.

TASK:
- Extract structured information.
- Return EXACTLY ONE JSON object.
- Return ONLY JSON.

OUTPUT RULES:
- Must start with { and end with }
- Must be valid json.loads()
- No markdown, explanations, or extra text
- Missing fields → null

STRING RULES:
- Use \\n for line breaks
- Escape quotes when needed
- Prefer rewriting to avoid quotes

RETURN EXACT STRUCTURE:

{
  "name": null,
  "email": null,
  "phone": null,
  "summary": null,
  "education": null,
  "experience": null,
  "skills": null,
  "projects": null,
  "certifications": null,
  "others": null
}
"""


class CVParser:
    """Comprehensive CV parsing with multiple extraction methods"""
    
    def __init__(self):
        self.groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
        self.nlp = nlp
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF using multiple methods"""
        text = ""
        
        try:
            # Method 1: PDFMiner (best for digital PDFs)
            text = pdf_extract_text(file_path)
            
            if text.strip():
                logger.info(f"✅ Extracted text using PDFMiner: {len(text)} chars")
                return text
            
        except Exception as e:
            logger.warning(f"PDFMiner failed: {e}")
        
        try:
            # Method 2: PDFPlumber (alternative for digital PDFs)
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            if text.strip():
                logger.info(f"✅ Extracted text using PDFPlumber: {len(text)} chars")
                return text
                
        except Exception as e:
            logger.warning(f"PDFPlumber failed: {e}")
        
        # Method 3: OCR fallback for scanned documents
        if not text.strip() and OCR_AVAILABLE:
            try:
                logger.info("Attempting OCR extraction...")
                with open(file_path, "rb") as f:
                    images = convert_from_bytes(f.read())
                
                for img in images:
                    text += pytesseract.image_to_string(img) + "\n"
                
                if text.strip():
                    logger.info(f"✅ Extracted text using OCR: {len(text)} chars")
                    return text
                    
            except Exception as e:
                logger.error(f"OCR extraction failed: {e}")
        
        return text
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            logger.info(f"✅ Extracted text from DOCX: {len(text)} chars")
            return text
        except Exception as e:
            logger.error(f"❌ Error extracting from DOCX: {e}")
            return ""
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from PDF or DOCX file"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return ""
        
        ext = file_path.suffix.lower()
        
        if ext == ".pdf":
            return self.extract_text_from_pdf(str(file_path))
        elif ext in [".docx", ".doc"]:
            return self.extract_text_from_docx(str(file_path))
        else:
            logger.error(f"Unsupported file format: {ext}")
            return ""
    
    def extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extract email and phone using regex"""
        # Email regex
        email_match = re.search(
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            text
        )
        email = email_match.group(0) if email_match else None
        
        # Phone regex (supports various formats)
        phone_pattern = r"(\+\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}"
        phone_matches = re.finditer(phone_pattern, text)
        phone = None
        
        for match in phone_matches:
            # Validate length
            digits_only = re.sub(r'\D', '', match.group(0))
            if len(digits_only) >= 10:
                phone = match.group(0).strip()
                break
        
        return {"email": email, "phone": phone}
    
    def extract_with_spacy(self, text: str) -> Dict:
        """Extract entities using Spacy NER"""
        if not self.nlp:
            return {}
        
        doc = self.nlp(text)
        
        # Extract name (first PERSON entity)
        name = None
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                # Simple heuristic: name should be 2-4 words, no newlines
                if "\n" not in ent.text and 2 <= len(ent.text.split()) <= 4:
                    name = ent.text.strip()
                    break
        
        # Extract skills (if custom entity ruler is set up)
        skills = set()
        for ent in doc.ents:
            if ent.label_ == "SKILL":
                skills.add(ent.text.title())
        
        # Extract experience years
        experience_years = 0
        exp_pattern = r"(\d+)\+?\s*years?"
        exp_matches = re.findall(exp_pattern, text.lower())
        if exp_matches:
            try:
                years = [int(y) for y in exp_matches]
                experience_years = max(years)
            except:
                pass
        
        return {
            "name": name,
            "skills": list(skills),
            "experience_years": experience_years
        }
    
    def clean_json_text(self, text: str) -> str:
        """Clean and fix JSON text from LLM output"""
        if not text:
            return None
        
        # Unicode normalization
        text = unicodedata.normalize("NFKC", text)
        
        # Remove PDFMiner CID artifacts
        text = re.sub(r'\(cid:\d+\)', '', text)
        
        # Remove illegal control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        
        # Normalize problematic unicode
        replacements = {
            "–": "-", "—": "-",
            """: '"', """: '"',
            "'": "'", "'": "'",
            "•": "-"
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        
        # Extract JSON
        start = text.find("{")
        end = text.rfind("}")
        
        if start == -1 or end == -1 or start >= end:
            return None
        
        json_text = text[start:end + 1]
        
        # Fix trailing commas
        json_text = re.sub(r',\s*([}\]])', r'\1', json_text)
        
        # Fix illegal backslashes
        json_text = re.sub(r'\\(?![\\nrt"/bfu])', r'\\\\', json_text)
        
        return json_text
    
    def parse_with_llm(self, text: str) -> Dict:
        """Parse resume using LLM (Groq)"""
        if not self.groq_client:
            logger.warning("Groq client not initialized. Skipping LLM parsing.")
            return {}
        
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text[:4000]}  # Limit text size
                ],
                temperature=0,
                max_completion_tokens=1024
            )
            
            raw_output = response.choices[0].message.content.strip()
            cleaned_json = self.clean_json_text(raw_output)
            
            if cleaned_json:
                parsed_data = json.loads(cleaned_json)
                logger.info("✅ Successfully parsed resume with LLM")
                return parsed_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"LLM parsing error: {e}")
        
        return {}
    
    def ensure_string(self, value):
        """Ensure value is a string or None"""
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip() or None
        if isinstance(value, dict):
            return "\n".join(f"{k}: {v}" for k, v in value.items())
        if isinstance(value, list):
            return "\n".join(str(v) for v in value)
        return str(value)
    
    def parse_resume(self, file_path: str) -> Dict:
        """
        Main method to parse a resume file
        Returns structured candidate data
        """
        logger.info(f"🔍 Parsing resume: {file_path}")
        
        # Extract raw text
        text = self.extract_text_from_file(file_path)
        
        if not text.strip():
            logger.error("No text extracted from file")
            return None
        
        # Initialize result
        result = {
            "name": "Unknown Candidate",
            "email": None,
            "phone": None,
            "summary": None,
            "education": None,
            "experience": None,
            "skills": None,
            "projects": None,
            "certifications": None,
            "others": None,
            "text_content": text,
            "experience_years": 0,
            "source_file": Path(file_path).name
        }
        
        # Method 1: LLM parsing (most comprehensive)
        llm_data = self.parse_with_llm(text)
        if llm_data:
            for key in ["name", "email", "phone", "summary", "education", 
                       "experience", "skills", "projects", "certifications", "others"]:
                if key in llm_data and llm_data[key]:
                    result[key] = self.ensure_string(llm_data[key])
        
        # Method 2: Regex extraction (for contact info)
        contact_info = self.extract_contact_info(text)
        if not result["email"]:
            result["email"] = contact_info["email"]
        if not result["phone"]:
            result["phone"] = contact_info["phone"]
        
        # Method 3: Spacy NER (for name and skills)
        spacy_data = self.extract_with_spacy(text)
        if not result["name"] or result["name"] == "Unknown Candidate":
            if spacy_data.get("name"):
                result["name"] = spacy_data["name"]
        
        if spacy_data.get("experience_years"):
            result["experience_years"] = spacy_data["experience_years"]
        
        # Fallback: use filename as name if still unknown
        if not result["name"] or result["name"] == "Unknown Candidate":
            result["name"] = Path(file_path).stem.replace("_", " ").title()
        
        logger.info(f"✅ Parsed resume for: {result['name']}")
        
        return result


def parse_cv_file(file_path: str) -> Dict:
    """Convenience function to parse a CV file"""
    parser = CVParser()
    return parser.parse_resume(file_path)


if __name__ == "__main__":
    # Test the CV parser
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    import sys
    
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    else:
        # Use a sample file if available
        test_file = "PDF_to_DB module/PDF_to_DB module/sample_document.pdf"
    
    if Path(test_file).exists():
        print(f"🧪 Testing CV Parser with: {test_file}\n")
        result = parse_cv_file(test_file)
        
        if result:
            print("=" * 60)
            print("PARSED DATA")
            print("=" * 60)
            for key, value in result.items():
                if key != "text_content":  # Skip full text
                    print(f"{key.upper()}: {value}")
        else:
            print("❌ Failed to parse resume")
    else:
        print(f"❌ File not found: {test_file}")
        print("Usage: python cv_parser.py <path_to_resume>")
