import logging
from pathlib import Path
import pydantic
import pytest
import sys
import yaml

# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from models import EmailData, HeaderAnalysis, EmailAction

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

def load_yaml_data(file_path):
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
        email = EmailData.model_validate(data["email"])
        analysis = HeaderAnalysis.model_validate(data["header_analysis"])
        if "action" in data:
            action = EmailAction.model_validate(data["action"])
        else:
            action = None
        return email, analysis, action

def get_test_cases():
    test_cases = {}
    for file in DATA_DIR.glob("*.yaml"):
        test_name = file.stem
        test_cases[test_name] = load_yaml_data(file)
    return test_cases

def get_test_cases_for_analysis():
    test_cases = {}
    for file in DATA_DIR.glob("*.yaml"):
        test_name = file.stem
        data = load_yaml_data(file)

        # Only include test cases with an action
        logger.debug(f"Loaded test case: {test_name} with data: {data}")
        if data[2] is not None:
            test_cases[test_name] = data

    return test_cases
