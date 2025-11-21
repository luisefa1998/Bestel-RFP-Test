import os
from pydantic import SecretStr
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenTextParamsMetaNames
from app.services.rate_limiter_service import get_rate_limiter


# Summarization parameters
SUMMARIZER_MAX_CONTEXT_LENGTH: int = 2 ** 13
FINAL_SUMMARIZER_MAX_CONTEXT_LENGTH: int = 2 ** 14

# LLMs parameters
slm_config = {
    "model_id": "ibm/granite-4-h-small",
    "url": SecretStr("https://us-south.ml.cloud.ibm.com"),
    "apikey": SecretStr(os.environ["WX_API_KEY"]),
    "project_id": os.environ["WX_PROJECT_ID"],
    "params": {
        GenTextParamsMetaNames.DECODING_METHOD: "sample",
        GenTextParamsMetaNames.TEMPERATURE: 0.3,
        GenTextParamsMetaNames.MAX_NEW_TOKENS: SUMMARIZER_MAX_CONTEXT_LENGTH/2,
        GenTextParamsMetaNames.REPETITION_PENALTY: 1.1
    },
    "rate_limiter": get_rate_limiter(),
}

llm_id = "openai/gpt-oss-120b"
llm_config = {
    "model_id": llm_id,
    "url": SecretStr("https://us-south.ml.cloud.ibm.com"),
    "apikey": SecretStr(os.environ["WX_API_KEY"]),
    "project_id": os.environ["WX_PROJECT_ID"],
    "params": {
        "temperature": 0.2,
        "max_tokens": SUMMARIZER_MAX_CONTEXT_LENGTH,
        "penalty_repetition": 1.1,
        "include_reasoning": False
    },
    "rate_limiter": get_rate_limiter(),
}
