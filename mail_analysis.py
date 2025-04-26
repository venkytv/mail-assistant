import abc
import llm
import logging
from typing import Any
import yaml

from models import EmailData, HeaderAnalysis, EmailAction, Notification, Task

logger = logging.getLogger(__name__)

class MailAnalyserBase(abc.ABC):
    """Base class for mail analyser"""

    def __init__(self, model, prompt_tag, response_schema, model_supports_schemas=True):
        self.model = llm.get_model(model)
        self.prompt_tag = prompt_tag
        self.response_schema = response_schema
        self.model_supports_schemas = model_supports_schemas
        self.samples = []

        with open("prompts.yaml", "r") as f:
            prompts = yaml.safe_load(f)
        if prompt_tag not in prompts:
            raise ValueError(f"Prompt tag '{prompt_tag}' not found in prompts.yml")
        self.prompt = prompts[prompt_tag]
        self.no_schema_instructions = prompts.get("no_schema_instructions", "")

    def add_sample(self, email: EmailData, response: Any):
        """Add a sample to the prompt"""
        self.samples.append((email, response))

    @abc.abstractmethod
    def prompt_data(self, email: EmailData) -> str:
        """Generate the prompt data for the email"""
        pass

    def get_prompt(self, email: EmailData) -> str:
        """Generate the prompt for the email"""
        if not self.model_supports_schemas and not self.samples:
            raise ValueError("Need at least one sample as the model does not support schemas")

        prompt_data = self.prompt_data(email)
        if not self.model_supports_schemas:
            prompt_data = f"user: {prompt_data}"

        samples = ""
        for email, response in self.samples:
            samples += f"user: {self.prompt_data(email)}\nassistant: {response.model_dump_json()}\n"

        prompt = self.prompt.format(prompt_data=prompt_data, samples=samples)

        if not self.model_supports_schemas:
            prompt = f"{prompt}\n\n{self.no_schema_instructions}"

        logger.debug("Prompt: %s", prompt)

        return prompt

    def process(self, email: EmailData) -> Any:
        """Process the email data and generate a response of the specified type"""

        # Generate the prompt for the email
        prompt = self.get_prompt(email)

        kwargs = {}
        if self.model_supports_schemas:
            kwargs["schema"] = self.response_schema
        response_data = self.model.prompt(prompt, **kwargs).text()
        logger.debug("Response data: %s", response_data)
        response = self.response_schema.model_validate_json(response_data)
        logger.debug("Response: %s", response)

        return response

class MailAnalyseCloud(MailAnalyserBase):
    """Analyse mail using cloud LLM"""

    def __init__(self, model, model_supports_schemas=True):
        super().__init__(
            model=model,
            prompt_tag="email_cloud",
            response_schema=HeaderAnalysis,
            model_supports_schemas=model_supports_schemas,
        )

    def prompt_data(self, email: EmailData) -> str:
        """Generate the prompt data"""
        return email.model_dump_json()

class MailAnalyse(MailAnalyserBase):
    """Analyse mail locally using the full email data"""

    def __init__(self, model, model_supports_schemas=True):
        super().__init__(
            model=model,
            prompt_tag="email_local",
            response_schema=EmailAction,
            model_supports_schemas=model_supports_schemas,
        )

    def prompt_data(self, email: EmailData) -> str:
        """Generate the prompt data for the full email"""
        return email.model_dump_json()
