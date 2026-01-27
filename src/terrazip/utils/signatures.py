import base64
import json
from urllib.parse import parse_qs
import re

from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256


def normalize_rsa2_public_key(public_key: str) -> str:
    """
    Normalize RSA2 public key to PEM format.

    - If PEM headers already exist, return as-is
    - If only base64 body is provided, wrap with PUBLIC KEY headers

    :param public_key: RSA2 public key (base64 or PEM)
    :return: PEM formatted public key
    """
    key = public_key.strip()

    # Already a PEM formatted public key
    if "BEGIN PUBLIC KEY" in key and "END PUBLIC KEY" in key:
        return key

    # Remove all whitespace/newlines
    key_body = "".join(key.split())

    return f"-----BEGIN PUBLIC KEY-----\n{key_body}\n-----END PUBLIC KEY-----"


def normalize_rsa2_private_key(private_key: str) -> str:
    """
    Normalize RSA2 private key to PEM format.

    Supports:
    - BEGIN RSA PRIVATE KEY
    - BEGIN PRIVATE KEY (PKCS#8)

    :param private_key: RSA2 private key (base64 or PEM)
    :return: PEM formatted private key
    """
    key = private_key.strip()

    # Already PEM formatted
    if "BEGIN RSA PRIVATE KEY" in key or "BEGIN PRIVATE KEY" in key:
        return key

    # Remove all whitespace/newlines
    key_body = "".join(key.split())

    # Default to PKCS#8 format
    return "-----BEGIN PRIVATE KEY-----\n" + key_body + "\n-----END PRIVATE KEY-----"


def _decode_payload(payload: bytes, content_type: str) -> str:
    """
    Decode payload using charset from Content-Type if provided.
    Fallback order:
      1. charset in Content-Type
      2. utf-8
      3. gb18030 (superset of gbk/gb2312)
    """
    # Try to extract charset from Content-Type
    match = re.search(r"charset=([^\s;]+)", content_type)
    if match:
        charset = match.group(1).strip('"').lower()
        return payload.decode(charset)

    # Fallbacks
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return payload.decode("gbk", ignore=True)


def process_payload_to_json(payload: bytes, headers: dict) -> dict:
    """
    Parses payload into a dict based on Content-Type.
    Supports:
      - application/json
      - application/x-www-form-urlencoded
    Handles utf-8 / gbk / gb2312 / gb18030 decoding.
    Raises errors directly if format is incorrect or unsupported.
    """
    # Normalize headers for case-insensitive access
    normalized_headers = {k.lower(): v for k, v in headers.items()}
    content_type = normalized_headers.get("content-type", "").lower()

    # Decode body (may raise UnicodeDecodeError)
    decoded_body = _decode_payload(payload, content_type)
        
    if "application/json" in content_type:
        # Invalid JSON -> json.JSONDecodeError
        return json.loads(decoded_body)

    elif "application/x-www-form-urlencoded" in content_type:
        parsed_data = parse_qs(
            decoded_body,
            strict_parsing=True,
            keep_blank_values=True,
        )
        return {k: v[0] if len(v) == 1 else v for k, v in parsed_data.items()}

    else:
        try:
            return json.loads(decoded_body.strip())
        except Exception as e:
            snippet = decoded_body[:500].strip()
            raise ValueError(
                "Received text/html response instead of structured data. "
                f"Possible upstream error page error:{e}.\n"
                f"Content-Type: {content_type}\n"
                f"Body preview:\n{snippet}"
            )

def sign_with_rsa2(params: dict, private_key_pem: str) -> str:
    """
    RSA2 signature
    """
    private_key_pem = normalize_rsa2_private_key(private_key_pem)
    unsigned_items = []
    for k in sorted(params.keys()):
        v = params[k]
        if v is None or v == "":
            continue
        unsigned_items.append(f"{k}={v}")
    unsigned_string = "&".join(unsigned_items)

    key = RSA.importKey(private_key_pem)
    signer = PKCS1_v1_5.new(key)
    digest = SHA256.new(unsigned_string.encode("utf-8"))
    signature = signer.sign(digest)

    return base64.b64encode(signature).decode("utf-8")


def verify_sign_rsa2(params: dict, sign: str, public_key_pem: str) -> bool:
    """
    Verify Alipay RSA2 signature (SHA256 with RSA, PKCS#1 v1.5)

    :param params: Parameters returned by Alipay (excluding 'sign')
    :param sign: Signature returned by Alipay (base64 encoded)
    :param public_key_pem: Alipay public key in PEM format
    :return: True if signature is valid, otherwise False
    """
    # Build the unsigned string in the same way as signing:
    # 1. Sort parameters by ASCII order
    # 2. Skip empty values and the 'sign' field
    # 3. Join as key=value pairs with '&'
    public_key_pem = normalize_rsa2_public_key(public_key_pem)
    unsigned_items = []
    for k in sorted(params.keys()):
        v = params[k]
        if v is None or v == "" or k == "sign":
            continue
        unsigned_items.append(f"{k}={v}")
    unsigned_string = "&".join(unsigned_items)

    # Load Alipay public key
    public_key = RSA.importKey(public_key_pem)
    verifier = PKCS1_v1_5.new(public_key)

    # Create SHA256 digest from the unsigned string
    digest = SHA256.new(unsigned_string.encode("utf-8"))

    # Decode base64 signature
    signature = base64.b64decode(sign)

    # Verify signature
    return verifier.verify(digest, signature)
