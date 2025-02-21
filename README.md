Email Analysis and Archiving System
=====================================

A personal email analysis and archiving system that uses a language model to
process email data and generate tasks, expense reports, or summaries based on
the email content.  This is designed for my personal use, and is probably a bit
idiosyncratic. But it might be useful as a starting point for someone else.

Overview
--------

This system consists of two main components: `mail-analyse.py` and
`mail-archiver.py`. The `mail-analyse.py` script is responsible for analyzing
email data and generating tasks, expense reports, or summaries based on the
email content. The `mail-archiver.py` script is a mail delivery agent (MDA)
that archives email messages by parsing them using `unstructured` and
publishing the result to a topic in NATS.

### Dependencies

- Python 3.12+
- [NATS server](https://nats.io/)
- [uv](https://docs.astral.sh/uv/getting-started/)
- [llm](https://llm.datasette.io/en/stable/)
- [getmail](https://getmail6.org/) (or similar mail retrieval agent)

### Installation

- Set up a NATS server
- Create a stream in NATS for the mail analysis and archiving system
  - Stream name: `emails`
  - Subjects: `email.parsed`
- Create a stream for email actions
  - Stream name: `email_actions`
  - Subjects: `email.action`
- Optionally, create a stream for error messages
  - Stream name: `email_errors`
  - Subjects: `email.error`
- If you want notifications to be stored, create a stream for notifications
  - Stream name: `notifications`
  - Subjects: `notifications.>`

### mail-archiver.py

#### Description

This script is a mail delivery agent (MDA) that archives email messages by
parsing them using `unstructured` and publishing the result to a topic in NATS.

#### Usage

The best way is to set up a small wrapper script that runs the
`mail-archiver.py` script using `uv`. Here is an example of such a script:
```bash
#!/bin/bash
cd ~/mail-assistant   # Assuming the script is in the ~/mail-assistant directory
exec uv run mail-archiver.py "$1"
```

And then hook it up to getmail, with a configuration like this in `~/.getmail/getmailrc`:
```ini
[retriever]
type = SimpleIMAPSSLRetriever
server = imap.example.com
username = my.username
password = my.password
mailboxes = ("INBOX",)
use_peercert = True

[destination]
type = MDA_external
path = /path/to/mail-archiver-wrapper.sh
arguments = ("%(sender)",)
ignore_stderr = True

[options]
read_all = False
delete = False
```

Now, run getmail to start the archive process:
```bash
getmail --verbose
```

You can customize the behavior of the script by using the following
command-line arguments:

* `--nats-server`: Specify the NATS server URL.
* `--nats-subject`: Specify the NATS subject to publish to.
* `--nats-error-subject`: Specify the NATS subject to publish errors to.

#### Functionality

The script performs the following steps:

1. Connects to the NATS server.
2. Reads the email message from standard input.
3. Parses the email message using `unstructured`.
4. Creates an `EmailData` object from the parsed email message.
5. Publishes the `EmailData` object to the specified NATS subject.
6. If an error occurs during parsing, publishes an `EmailParseError` object to the specified NATS error subject.

### mail-analyse.py

#### Description

This script analyzes email data and generates tasks, expense reports, or
summaries based on the email content. It uses a language model to process the
email data and generate a response.

#### Usage

To use this script, run it with the following command:
```bash
uv run mail-analyse.py
```
You can customize the behavior of the script by using the following command-line arguments:

* `--model`: Specify the language model to use for analysis.
* `--nats`: Specify the NATS server URL.
* `--nats-stream`: Specify the NATS stream to subscribe to.
* `--nats-consumer`: Specify the NATS consumer name.
* `--nats-subject`: Specify the NATS subject to publish actions to.
* `--nats-notification-subject`: Specify the NATS subject to publish notifications to.
* `--limit`: Specify the number of messages to process.
* `--debug`: Enable debug logging.

#### Functionality

The script performs the following steps:

1. Connects to the NATS server and subscribes to the specified stream.
2. Loads the specified language model.
3. Processes each message in the stream using the language model.
4. Generates a response based on the email content.
5. Publishes the response to the specified NATS subject.
