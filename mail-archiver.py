#!/usr/bin/env python3

# MDA that gets invoked by getmail to archive mail. The script parses the email
# using `unstructured` and publishes the result to a topic in NATS.

import argparse
import asyncio
from datetime import datetime
import nats
import pydantic
import sys
from tempfile import NamedTemporaryFile
from unstructured.partition.email import partition_email

class EmailData(pydantic.BaseModel):
    from_: list[str]
    to: list[str]
    subject: str
    date: str
    message_id: str
    body: str

class EmailParseError(pydantic.BaseModel):
    sender: str
    date: str
    error: str

async def main():
    parser = argparse.ArgumentParser(
        description="Archive email messages",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--nats-server", "-s", default="nats://localhost:4222", help="NATS server URL")
    parser.add_argument("--nats-subject", default="email.parsed", help="NATS subject to publish to")
    parser.add_argument("--nats-error-subject", default="email.error", help="NATS subject to publish errors to")
    parser.add_argument("sender", help="Email sender")
    args = parser.parse_args()

    nc = await nats.connect(args.nats_server)

    try:
        email = sys.stdin.buffer.read()

        with NamedTemporaryFile(delete_on_close=False) as f:
            f.write(email)
            f.close()

            # Parse email using unstructured
            elements = partition_email(filename=f.name)
    except Exception as e:
        # Publish error to NATS
        error = EmailParseError(sender=args.sender, date=str(datetime.now()), error=str(e))
        await nc.publish(args.nats_error_subject, error.model_dump_json().encode())
        return

    # Parsed email data
    data = EmailData(
        from_=elements[0].metadata.sent_from,
        to=elements[0].metadata.sent_to,
        subject=elements[0].metadata.subject,
        date=elements[0].metadata.last_modified,
        message_id=elements[0].metadata.email_message_id,
        body="\n\n".join([str(el) for el in elements]),
    )

    # Publish parsed email data to NATS
    await nc.publish(args.nats_subject, data.model_dump_json().encode())

if __name__ == '__main__':
    asyncio.run(main())
