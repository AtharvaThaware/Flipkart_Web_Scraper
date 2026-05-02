# ─────────────────────────────────────────────────────────────────────────────
# exporter.py — Data export (Excel / CSV / JSON / SQL) and email delivery
#
# Responsibilities:
#   • build_export()               — serialize a DataFrame to bytes
#   • send_email_with_attachment() — send the exported file via Gmail SMTP
#
# Why smtplib instead of yagmail?
# ────────────────────────────────
# yagmail stores credentials in the OS keyring (a per-OS-session resource).
# Streamlit forks a new Python subprocess on every rerun, so the keyring
# lookup fails silently → SMTPAuthenticationError even with correct creds.
# smtplib avoids the keyring entirely: credentials are passed in-memory
# on every call.
# ─────────────────────────────────────────────────────────────────────────────
import smtplib
import re
from email.message import EmailMessage
from io import BytesIO
import pandas as pd
from config import SMTP_HOST, SMTP_PORT


# ── File export ───────────────────────────────────────────────────────────────

def build_export(df: pd.DataFrame, fmt: str, query: str) -> tuple[bytes, str, str]:
    """
    Serialize *df* into the chosen format and return a 3-tuple:
        (file_bytes, filename, mime_type)

    Args:
        df:    The scraped product DataFrame.
        fmt:   One of "Excel", "CSV", "JSON", "SQL".
        query: The original search query — used to build the filename.

    Returns:
        file_bytes  — raw bytes ready for st.download_button or email attachment
        filename    — suggested filename with extension
        mime_type   — MIME type string

    Raises:
        ValueError  — if *fmt* is not one of the four supported formats.
    """
    safe_q = _safe_filename(query)

    if fmt == "Excel":
        return _to_excel(df, safe_q)

    if fmt == "CSV":
        return _to_csv(df, safe_q)

    if fmt == "JSON":
        return _to_json(df, safe_q)

    if fmt == "SQL":
        return _to_sql(df, safe_q)

    raise ValueError(f"Unsupported export format: '{fmt}'")


# ── Email delivery ────────────────────────────────────────────────────────────

def send_email_with_attachment(
    from_addr:        str,
    password:         str,
    to_addr:          str,
    subj:             str,
    body:             str,
    attachment_bytes: bytes,
    attachment_name:  str,
) -> None:
    """
    Send an email with a file attachment via Gmail SMTP (STARTTLS, port 587).

    Args:
        from_addr:        Sender's Gmail address.
        password:         Gmail App Password (NOT the regular account password).
                          Generate at myaccount.google.com → Security → App Passwords.
        to_addr:          Recipient email address.
        subj:             Email subject line.
        body:             Plain-text email body.
        attachment_bytes: Raw bytes of the file to attach.
        attachment_name:  Filename shown in the email (including extension).

    Raises:
        smtplib.SMTPAuthenticationError — wrong credentials / App Password not set up.
        smtplib.SMTPException           — any other SMTP-level error.
        OSError                         — network connectivity issues.
    """
    msg            = EmailMessage()
    msg["Subject"] = subj
    msg["From"]    = from_addr
    msg["To"]      = to_addr
    msg.set_content(body)

    # Auto-detect MIME type from file extension
    maintype, subtype = _mime_for_extension(attachment_name)
    msg.add_attachment(
        attachment_bytes,
        maintype=maintype,
        subtype=subtype,
        filename=attachment_name,
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(from_addr, password)
        server.send_message(msg)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _safe_filename(query: str) -> str:
    """Replace non-alphanumeric characters with underscores."""
    return re.sub(r"[^\w]", "_", query)


def _to_excel(df: pd.DataFrame, safe_q: str) -> tuple[bytes, str, str]:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Products")
    return (
        buf.getvalue(),
        f"{safe_q}_flipkart.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _to_csv(df: pd.DataFrame, safe_q: str) -> tuple[bytes, str, str]:
    return (
        df.to_csv(index=False).encode(),
        f"{safe_q}_flipkart.csv",
        "text/csv",
    )


def _to_json(df: pd.DataFrame, safe_q: str) -> tuple[bytes, str, str]:
    return (
        df.to_json(orient="records", indent=2).encode(),
        f"{safe_q}_flipkart.json",
        "application/json",
    )


def _to_sql(df: pd.DataFrame, safe_q: str) -> tuple[bytes, str, str]:
    """
    Generate a series of INSERT INTO statements.
    Single quotes inside values are escaped by doubling them ('').
    """
    col_names = ", ".join(df.columns)
    lines = []
    for _, row in df.iterrows():
        vals = ", ".join(
            "'{}'".format(str(v).replace("'", "''")) for v in row
        )
        lines.append(f"INSERT INTO products ({col_names}) VALUES ({vals});")
    return (
        "\n".join(lines).encode(),
        f"{safe_q}_flipkart.sql",
        "text/plain",
    )


def _mime_for_extension(filename: str) -> tuple[str, str]:
    """Return (maintype, subtype) MIME pair based on file extension."""
    ext = filename.rsplit(".", 1)[-1].lower()
    mime_map = {
        "xlsx": ("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "csv":  ("text",        "csv"),
        "json": ("application", "json"),
        "sql":  ("text",        "plain"),
    }
    return mime_map.get(ext, ("application", "octet-stream"))
