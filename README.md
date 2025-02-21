Email Analysis and Archiving System
=====================================

Overview
--------

This system consists of two main components: `mail-analyse.py` and `mail-archiver.py`. The `mail-analyse.py` script is responsible for analyzing email data and generating tasks, expense reports, or summaries based on the email content. The `mail-archiver.py` script is a mail delivery agent (MDA) that archives email messages by parsing them using `unstructured` and publishing the result to a topic in NATS.

### mail-analyse.py

#### Description

This script analyzes email data and generates tasks, expense reports, or summaries based on the email content. It uses a language model to process the email data and generate a response.

#### Usage

To use this script, run it with the following command:
```bash
python mail-analyse.py
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

### mail-archiver.py

#### Description

This script is a mail delivery agent (MDA) that archives email messages by parsing them using `unstructured` and publishing the result to a topic in NATS.

#### Usage

To use this script, run it with the following command:
```bash
python mail-archiver.py
```
You can customize the behavior of the script by using the following command-line arguments:

* `--nats-server`: Specify the NATS server URL.
* `--nats-subject`: Specify the NATS subject to publish to.
* `--nats-error-subject`: Specify the NATS subject to publish errors to.
* `sender`: Specify the email sender.

#### Functionality

The script performs the following steps:

1. Connects to the NATS server.
2. Reads the email message from standard input.
3. Parses the email message using `unstructured`.
4. Creates an `EmailData` object from the parsed email message.
5. Publishes the `EmailData` object to the specified NATS subject.
6. If an error occurs during parsing, publishes an `EmailParseError` object to the specified NATS error subject.
