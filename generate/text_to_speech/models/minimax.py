from __future__ import annotations

import os
from typing import Any, ClassVar, List, Literal, Optional

import httpx
from httpx import Response
from pydantic import Field, model_validator
from typing_extensions import Annotated, Self, TypedDict, Unpack, override

from generate.http import HttpModelInitKwargs, HttpxPostKwargs, UnexpectedResponseError
from generate.parameters import ModelParameters
from generate.text_to_speech.http_speech import HttpSpeechModel
from generate.text_to_speech.model_output import TextToSpeechModelOutput


class TimeberWeight(TypedDict):
    voice_id: str
    weight: int


class MinimaxSpeechParameters(ModelParameters):
    voice_id: Optional[str] = None
    speed: Annotated[Optional[float], Field(ge=0.5, le=2.0)] = None
    vol: Annotated[Optional[float], Field(gt=0, le=10)] = None
    pitch: Annotated[Optional[float], Field(ge=-12, le=12)] = None
    timber_weights: Annotated[Optional[List[TimeberWeight]], Field(min_length=1, max_length=4)] = None

    @model_validator(mode='after')
    def voice_exists(self) -> Self:
        if self.voice_id is None and self.timber_weights is None:
            self.voice_id = 'male-qn-qingse'
        return self


class MinimaxProSpeechParameters(MinimaxSpeechParameters):
    audio_sample_rate: Annotated[Optional[int], Field(ge=16000, le=24000)] = 24000
    bitrate: Literal[32000, 64000, 128000] = 128000


class MinimaxSpeech(HttpSpeechModel[MinimaxSpeechParameters]):
    model_type = 'minimax'
    default_api_base: ClassVar[str] = 'https://api.minimax.chat/v1/text_to_speech'

    def __init__(
        self,
        model: str = 'speech-01',
        group_id: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
        parameters: MinimaxSpeechParameters | None = None,
        **kwargs: Unpack[HttpModelInitKwargs],
    ) -> None:
        parameters = parameters or MinimaxSpeechParameters()
        super().__init__(parameters, **kwargs)
        self.model = model
        self.group_id = group_id or os.environ['MINIMAX_GROUP_ID']
        self.api_key = api_key or os.environ['MINIMAX_API_KEY']
        self.api_base = api_base or self.default_api_base

    @override
    def _get_request_parameters(self, text: str, parameters: MinimaxSpeechParameters) -> HttpxPostKwargs:
        parameters_dict = parameters.model_dump(exclude_none=True, by_alias=True)
        json_data = {
            'model': self.model,
            'text': text,
            **parameters_dict,
        }
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        return {
            'url': self.api_base,
            'json': json_data,
            'headers': headers,
            'params': {'GroupId': self.group_id},
        }

    @override
    def _construct_model_output(
        self, text: str, parameters: MinimaxSpeechParameters, response: Response
    ) -> TextToSpeechModelOutput:
        return TextToSpeechModelOutput(
            speech_model_id=self.model_id,
            audio=response.content,
            audio_format='mp3',
            cost=self.calculate_cost(text),
        )

    @property
    @override
    def name(self) -> str:
        return self.model

    @classmethod
    @override
    def from_name(cls, name: str, **kwargs: Any) -> Self:
        return cls(model=name, **kwargs)

    @staticmethod
    def calculate_cost(text: str) -> float:
        character_count = sum(2 if '\u4e00' <= char <= '\u9fff' else 1 for char in text)
        return character_count / 1000


class MinimaxProSpeech(HttpSpeechModel[MinimaxProSpeechParameters]):
    model_type = 'minimax_pro'
    default_api_base: ClassVar[str] = 'https://api.minimax.chat/v1/t2a_pro'

    def __init__(
        self,
        model: str = 'speech-01',
        group_id: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
        parameters: MinimaxProSpeechParameters | None = None,
        **kwargs: Unpack[HttpModelInitKwargs],
    ) -> None:
        parameters = parameters or MinimaxProSpeechParameters()
        super().__init__(parameters, **kwargs)
        self.model = model
        self.group_id = group_id or os.environ['MINIMAX_GROUP_ID']
        self.api_key = api_key or os.environ['MINIMAX_API_KEY']
        self.api_base = api_base or self.default_api_base

    @override
    def _get_request_parameters(self, text: str, parameters: MinimaxProSpeechParameters) -> HttpxPostKwargs:
        parameters_dict = parameters.model_dump(exclude_none=True, by_alias=True)
        json_data = {
            'model': self.model,
            'text': text,
            **parameters_dict,
        }
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        return {
            'url': self.api_base,
            'json': json_data,
            'headers': headers,
            'params': {'GroupId': self.group_id},
        }

    @override
    def _construct_model_output(
        self, text: str, parameters: MinimaxProSpeechParameters, response: Response
    ) -> TextToSpeechModelOutput:
        response_data = response.json()
        if response_data['base_resp']['status_code'] != 0:
            raise UnexpectedResponseError(response_data)

        model_output = TextToSpeechModelOutput(
            speech_model_id=self.model_id,
            audio=httpx.get(response_data['audio_file']).content,
            audio_format='mp3',
            cost=response_data['extra_info']['word_count'] / 1000,
        )
        model_output.debug['http_response'] = response_data
        model_output.extra['subtitle'] = httpx.get(response_data['subtitle_file']).json()
        model_output.extra.update(response_data['extra_info'])
        return model_output

    @property
    @override
    def name(self) -> str:
        return self.model

    @classmethod
    @override
    def from_name(cls, name: str, **kwargs: Any) -> Self:
        return cls(model=name, **kwargs)