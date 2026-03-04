"""
Check if an SES identity (email or domain) is verified.
"""
import boto3
import sys

REGION = "ap-south-1"


def check_identity_verified(identity: str, region: str = REGION) -> bool:
    """Check if an SES identity is verified. Returns True if verified, False otherwise."""
    ses = boto3.client("ses", region_name=region)
    resp = ses.get_identity_verification_attributes(Identities=[identity])
    attrs = resp.get("VerificationAttributes", {})
    if identity not in attrs:
        return False
    status = attrs[identity].get("VerificationStatus", "")
    return status == "Success"


def main():
    identity = sys.argv[1] if len(sys.argv) > 1 else "shahin.sheikh1337@proton.me"
    verified = check_identity_verified(identity)
    status = "verified" if verified else "not verified"
    print(f"{identity}: {status}")
    sys.exit(0 if verified else 1)


if __name__ == "__main__":
    main()

#"""
#AWS SES script: create an identity and send email.
#NOTE: In sandbox mode, both sender and recipient must be verified identities.
#"""
#
#import boto3
#import time
#
#REGION = "ap-south-1"  # Change if your SES is in another region
#
#
#def create_identity(ses_client, email: str) -> None:
#    """Verify an email identity. SES sends a verification link to the address."""
#    ses_client.verify_email_identity(EmailAddress=email)
#    print(f"Verification email sent to {email}. Check inbox and click the link.")
#
#
#def send_email(
#    ses_client,
#    *,
#    from_addr: str,
#    to_addr: str,
#    subject: str,
#    body_text: str,
#    body_html: str | None = None,
#) -> dict:
#    """Send an email via SES."""
#    kwargs = {
#        "Source": from_addr,
#        "Destination": {"ToAddresses": [to_addr]},
#        "Message": {
#            "Subject": {"Data": subject, "Charset": "UTF-8"},
#            "Body": {"Text": {"Data": body_text, "Charset": "UTF-8"}},
#        },
#    }
#    if body_html:
#        kwargs["Message"]["Body"]["Html"] = {"Data": body_html, "Charset": "UTF-8"}
#    return ses_client.send_email(**kwargs)
#
#
#def main():
#    ses = boto3.client("ses", region_name=REGION)
#
#    # In sandbox: verify sender and recipient before sending
#    sender = "shahin.sheikh1337@proton.me"  # Replace with your email
#    recipient = "xenxiao80@gmail.com"  # Replace with recipient email
#
#    print("Step 1: Verifying identities (required in sandbox mode)...")
#    create_identity(ses, sender)
#    create_identity(ses, recipient)
#    print("Check both inboxes and complete verification before continuing.")
#    print("Waiting 60s for you to verify... (Ctrl+C to skip)")
#    try:
#        time.sleep(60)
#    except KeyboardInterrupt:
#        print("\nSkipped wait.")
#
#    print("\nStep 2: Sending email...")
#    resp = send_email(
#        ses,
#        from_addr=sender,
#        to_addr=recipient,
#        subject="Test from AWS SES",
#        body_text="This is a test email sent via AWS SES.",
#        body_html="<p>This is a test email sent via <b>AWS SES</b>.</p>",
#    )
#    print(f"Email sent! MessageId: {resp['MessageId']}")
#
#
#if __name__ == "__main__":
#    main()
#