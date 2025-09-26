# src/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Loads and validates application settings from environment variables.
    """
    # Load variables from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

    print(f"Settings: {model_config}")

    # Slack settings
    SLACK_BOT_TOKEN: str

    # # Jira settings
    JIRA_BASE_URL: str
    JIRA_USER_EMAIL: str
    JIRA_API_TOKEN: str
    OPENAI_API_KEY: str
    GOOGLE_API_KEY: str
    SLACK_ESCALATION_CHANNEL_ID: str # Add this line

# Create a single, importable instance of the settings
settings = Settings()