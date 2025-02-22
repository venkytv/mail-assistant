import argparse
import asyncio
from collections.abc import Callable
from enum import Enum
import json
import llm
import logging
import nats
import os
import pydantic
import re
import sys

from models import EmailData, Notification, Task

logger = logging.getLogger(__name__)

handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)

logger.setLevel(logging.INFO)

prompt_header = """
Analyse the email data and do one of the following:
1. Check if there is a something that needs to be done and generate a task for
   it with a due date, if necessary. Prefix this with "Task: ". If there is a
   due date, use the format "Task: [Due: <due_date_time>] <task>" instead.
2. Check if there is a record of an expense and generate a report for it.
   Prefix this with "Expense: ".
3. If neither of the above, generate a one-line summary of the email. Prefix
   this with "Summary: ".
"""

prompt_footer = """
- Provide just the response without ABSOLUTELY NO ADDITIONAL COMMENTARY on the
  actions you took or justifications for the same.
- Each response should be a single line.
- Add a suffix of the format "(<email_id>, <date>)" to each response.
- If the action or summary is important or urgent, add a prefix of "[IMP]" or
  "[URG]" respectively.
- If the email is spam or irrelevant, add a prefix of "[SPAM]", but still include
  a one-line summary of the email.
"""

class DestinationType(str, Enum):
    NOTIFICATION = "Email Notification"
    TASK = "Email Task"
    DEFAULT = "Default"

class Destination(pydantic.BaseModel):
    type: DestinationType
    action: str
    due_date: str = ""

# Determine the NATS destinations based on the action text
def get_destinations(action) -> list[Destination]:
    destinations = []

    # Add default destination
    destinations.append(
        Destination(
            type=DestinationType.DEFAULT,
            action=action,
        ))

    # Check if the action is important or urgent
    if "[IMP]" in action or "[URG]" in action:
        destinations.append(
            Destination(
                type=DestinationType.NOTIFICATION,
                action=action,
            ))

        # Strip the "[IMP]" or "[URG]" prefix for subsequent processing
        action = re.sub(r"^\[(?:IMP|URG)\]\s*", "", action)

    # Check if the action is a task
    # Example: Task: [Due: 2021-09-30 12:00] Send the report (me@example.com, 2025-02-22T09:07:27+00:00)
    if action.startswith("Task:"):
        # Strip the "Task:" prefix
        action = re.sub(r"^Task:\s*", "", action)

        # Extract the due date, if present
        match = re.match(r"^\[Due:\s*([^\]]+)\]\s*(.*)$", action)
        if match:
            due_date = match.group(1)
            action = match.group(2)
        else:
            due_date = ""

        # Strip the trailing (from, date) suffix
        action = re.sub(r"\s*\([^\)]+\)$", "", action)

        destinations.append(
            Destination(
                type=DestinationType.TASK,
                action=action,
                due_date=due_date,
            ))

    return destinations

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

def destination_content(destination_subjects: dict[str, str]) -> Callable[[Destination], tuple[str, str]]:
    """Return a closure that can be used to serialise a message for a destination"""
    task_serialiser = lambda destination: Task(
        action=destination.action,
        due_date=destination.due_date).model_dump_json()
    notification_serialiser = lambda destination: Notification(
        title=destination.type.value,
        message=destination.action).model_dump_json()
    destination_map = {
        DestinationType.NOTIFICATION: (
            destination_subjects[DestinationType.NOTIFICATION],
            notification_serialiser),
        DestinationType.TASK: (
            destination_subjects[DestinationType.TASK],
            task_serialiser),
        DestinationType.DEFAULT: (
            destination_subjects[DestinationType.DEFAULT],
            lambda x: x.action),
    }

    def serialise(destination) -> tuple[str, str]:
        subject, serialiser = destination_map[destination.type]
        return subject, serialiser(destination)

    return serialise

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
    parser.add_argument("--nats-task-subject", default="tasks.email.action",
                        help="NATS subject to publish tasks to")
    parser.add_argument("--nats-notification-subject",
                        default="notifications.email.action",
                        help="NATS subject to publish notifications to")
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

    destination_subjects = {
        DestinationType.NOTIFICATION: args.nats_notification_subject,
        DestinationType.TASK: args.nats_task_subject,
        DestinationType.DEFAULT: args.nats_subject,
    }
    content = destination_content(destination_subjects)

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

                destinations = get_destinations(action)
                for destination in destinations:
                    subject, body = content(destination)
                    logger.debug("Publishing action to %s", subject)
                    await nc.publish(subject, body)

        except nats.errors.TimeoutError:
            logger.debug("Timeout waiting for messages, exiting")
            break

    await nc.close()

if __name__ == '__main__':
    asyncio.run(main())
