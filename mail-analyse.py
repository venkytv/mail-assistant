import argparse
import asyncio
import llm
import logging
import nats
import os
import pydantic
import sys

from models import EmailData

logger = logging.getLogger(__name__)

handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)

logger.setLevel(logging.INFO)

prompt_header = """
Analyse the email data and do one of the following:
1. Check if there is a something that needs to be done and generate a task for
   it with a due date, if necessary. Prefix this with "Task: ".
2. Check if there is a record of an expense and generate a report for it.
   Prefix this with "Expense: ".
3. If neither of the above, generate a one-line summary of the email. Prefix
   this with "Summary: ".
"""

prompt_footer = """
- Provide just the response without ABSOLUTELY NO ADDITIONAL COMMENTARY on the
  actions you took or justifications for the same.
- Add a suffix of the format "(<email_id>, <date>)" to each response.
"""

async def process(model, email) -> str:
    prompt = f"""{prompt_header}

    Email data:
    From: {", ".join(email.from_)}
    To: {", ".join(email.to)}
    Subject: {email.subject}
    Date: {email.date}
    Body: {email.body}

    {prompt_footer}
    """

    response = model.prompt(prompt)
    return response.text()

async def main():
    default_model = os.environ.get("MODEL",
                                   "mlx-community/Llama-3.2-3B-Instruct-4bit")
    default_nats = os.environ.get("NATS", "nats://localhost:4222")

    parser = argparse.ArgumentParser(
        description="Analyse emails",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--model", default=default_model,
                        help="Model to use for analysis")
    parser.add_argument("--nats", default=default_nats,
                        help="NATS server URL")
    parser.add_argument("--nats-stream", default="emails",
                        help="NATS stream to subscribe to")
    parser.add_argument("--nats-consumer", default="email-analyser",
                        help="NATS consumer name")
    parser.add_argument("--nats-subject", default="email.action",
                        help="NATS subject to publish actions to")
    parser.add_argument("--limit", type=int, default=50,
                        help="Number of messages to process (-1 for all)")
    parser.add_argument("--debug", action=argparse.BooleanOptionalAction,
                        help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    logger.debug("Connecting to NATS server at %s", args.nats)
    nc = await nats.connect(args.nats)
    js = nc.jetstream()

    logger.debug("Loading model %s", args.model)
    model = llm.get_model(args.model)

    # Set up a pull consumer for the stream
    logger.debug("Subscribing to stream %s", args.nats_stream)
    psub = await js.pull_subscribe("", stream=args.nats_stream,
                                   durable=args.nats_consumer)

    count = args.limit
    while count > 0:
        count -= 1

        try:
            msgs = await psub.fetch(batch=1, timeout=10)
            if not msgs:
                logger.debug("No messages received, exiting")
                break

            for msg in msgs:
                await msg.ack()
                raw_data = msg.data.decode()
                logger.debug("Received message: %s", raw_data)

                try:
                    email = EmailData.model_validate_json(raw_data)
                except pydantic.ValidationError as e:
                    logger.error("Error validating email: %s: %s", e, raw_data)
                    continue

                action = await process(model, email)
                logger.info(action)

                logger.debug("Publishing action to %s", args.nats_subject)
                await nc.publish(args.nats_subject, action.encode())
        except nats.errors.TimeoutError:
            logger.debug("Timeout waiting for messages, exiting")
            break

    await nc.close()

if __name__ == '__main__':
    asyncio.run(main())
