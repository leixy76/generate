from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict

from generate.platforms.openai_like import OpenAILikeSettings


class OpenRouterSettings(OpenAILikeSettings):
    model_config = SettingsConfigDict(extra='ignore', env_prefix='openrouter_', env_file='.env')

    api_key: SecretStr
    api_base: str = 'https://openrouter.ai/api/v1'
    platform_url: str = 'https://openrouter.ai/'
