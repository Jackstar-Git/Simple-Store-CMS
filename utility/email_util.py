from logging_utility import logger
import re
import requests
import smtplib
import json
from email import encoders
from email.mime.base import MIMEBase    
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from io import BytesIO

from .data_managment import get_settings


# =====================================
# Email Functions
# =====================================

# Send an email with optional attachments
def send_email(recipients: list[str], bcc: list[str], subject, body, files=None):
    mail_settings: dict = get_settings("email_settings")
    sender_email = mail_settings.get("address")

    try:
        # Setup email message
        message = MIMEMultipart()
        message["From"] = "Birdie Club GmbH"
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message["Bcc"] = ", ".join(bcc)

        all_recipients = recipients + bcc
        message.attach(MIMEText(body, "html"))

        # Attach files if provided
        if files is not None:
            if isinstance(files, BytesIO):
                files.seek(0)
                part = MIMEBase("application", "octet-stream")
                part.set_payload(files.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename=invoice.pdf")
                message.attach(part)

        # Send the email
        smtp_server = smtplib.SMTP(mail_settings.get("smtp-server", mail_settings.get("smtp-port")))
        smtp_server.starttls()
        smtp_server.login(sender_email, mail_settings.get("password"))
        smtp_server.sendmail(sender_email, all_recipients, message.as_string())
        smtp_server.quit()

        logger.info(f"Successfully sent an email to '{sender_email}' with the subject '{subject}'")

    except Exception as e:
        logger.error(f"Error occurred while sending email: {e}")
        print(f"Error occurred: {e}")

def send_http_email(recipients: list[str], subject, body, files=None, bcc: list[str] = None):
    pass



# =====================================
# Markdown to HTML Conversion Functions
# =====================================

# Convert markdown text to HTML format
def convert_markdown_to_html(markdown_text: str) -> str:
    try:
        translation_table = str.maketrans({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
        })
        
        patterns = [
            (re.compile(r'\*\*\*(.+?)\*\*\*'), r'<strong><em>\1</em></strong>'),
            (re.compile(r'\*\*(.+?)\*\*'), r'<strong>\1</strong>'),          
            (re.compile(r'\*(.+?)\*'), r'<em>\1</em>'),                        
            (re.compile(r'~~(.+?)~~'), r'<s>\1</s>'),                         
            (re.compile(r'_(.+?)_'), r'<u>\1</u>'),                               
            (re.compile(r'\{color:(#[0-9a-fA-F]{3,6})\}(.*?)\{\/color\}', re.DOTALL), r'<span style="color:\1">\2</span>'),
            (re.compile(r'\{align:([a-z]*)\}(.*?)\{\/align\}', re.DOTALL), r'<span style="display: block; text-align:\1">\2</span>'),
            (re.compile(r'\[(.+?)\]\((.+?)\)'), r'<a href="\2">\1</a>'),        
            (re.compile(r'`(.+?)`'), r'<code>\1</code>')
        ]

        html_output_list: list = []

        line_iter = iter(markdown_text.splitlines())

        in_codeblock = False
        in_list = False
        in_blockquote = False
        in_html = False

        # Process each line of markdown text
        for line in line_iter:
            if line.strip().startswith(r"{html}"):
                in_html = True
                continue
            if line.strip().startswith(r"{/html}"):
                in_html = False
                continue
            
            if in_html:
                html_output_list.append(line)
                continue

            # Handle code blocks
            if line.strip().startswith('```'):
                if in_codeblock:
                    html_output_list.append('</pre>')
                    in_codeblock = False
                else:
                    html_output_list.append('<pre>')
                    in_codeblock = True
                continue

            if in_codeblock:
                line = line.translate(translation_table)
                html_output_list.append(line)
                continue

            if in_list and not line.strip().startswith('- '):
                html_output_list.append('</ul>')
                in_list = False
            
            if in_blockquote and not line.strip().startswith('> '):
                html_output_list.append('</blockquote>')
                in_blockquote = False

            # Apply markdown patterns to the current line
            for pattern, replacement in patterns:
                line = pattern.sub(replacement, line)

            # Handle empty lines
            if line.strip() == "":
                html_output_list.append("<br>")
                continue

            # Handle headers
            if line.strip().startswith('#'):
                header_level = len(re.match(r'#+', line).group(0))
                header_content = line[header_level:].strip()
                html_output_list.append(f'<h{header_level}>{header_content}</h{header_level}>')
                continue

            # Handle horizontal rules
            if line.strip().startswith("---"):
                html_output_list.append("<hr>")
                continue

            # Handle unordered lists
            if line.strip().startswith('- '):
                if not in_list:
                    in_list = True
                    html_output_list.append('<ul>')
                html_output_list.append(f'\t<li>{line[2:].strip()}</li>')
                continue

            # Handle blockquotes
            if line.strip().startswith('> '):
                if not in_blockquote:
                    in_blockquote = True
                    html_output_list.append('<blockquote>')
                html_output_list.append(line[2:].strip())
                continue

            # Handle paragraphs (default case)
            html_output_list.append(f'<p>{line.strip()}</p>')

        # Close any open tags
        if in_list:
            html_output_list.append('</ul>')
        if in_blockquote:
            html_output_list.append('</blockquote>')
        if in_codeblock:
            html_output_list.append('</pre>')

        # Join the HTML output into a single string
        html_output: str = "\n".join(html_output_list)

        logger.info("Markdown successfully converted to HTML.")
        return html_output

    except Exception as e:
        logger.error(f"Error converting markdown to HTML: {e}")
        return markdown_text 
