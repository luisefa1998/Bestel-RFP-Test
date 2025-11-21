from typing import Optional
from langchain_ibm import ChatWatsonx
from .config import slm_config, llm_config
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from .prompts import (
    MAP_SUMMARIZATION,
    MAP_SUMMARIZATION_WITH_QUERY,
    REDUCE_SUMMARIZATION,
    REDUCE_SUMMARIZATION_WITH_QUERY,
    EXECUTIVE_SUMMARIZATION
)


def get_map_chain(user_query: Optional[str] = None):
    """Get map summarization chain, optionally with user query"""
    if user_query:
        return (
            PromptTemplate(
                template=MAP_SUMMARIZATION_WITH_QUERY,
                input_variables=["input_text", "user_query"]
            )
            | ChatWatsonx(**slm_config)
            | StrOutputParser()
        )
    return (
        PromptTemplate(template=MAP_SUMMARIZATION, input_variables=["input_text"])
        | ChatWatsonx(**slm_config)
        | StrOutputParser()
    )


def get_reduce_chain(user_query: Optional[str] = None):
    """Get reduce summarization chain, optionally with user query"""
    if user_query:
        return (
            PromptTemplate(
                template=REDUCE_SUMMARIZATION_WITH_QUERY,
                input_variables=["input_summaries", "user_query"]
            )
            | ChatWatsonx(**slm_config)
            | StrOutputParser()
        )
    return (
        PromptTemplate(template=REDUCE_SUMMARIZATION, input_variables=["input_summaries"])
        | ChatWatsonx(**slm_config)
        | StrOutputParser()
    )


def get_final_chain(user_query: Optional[str] = None):
    """Get final summarization chain, optionally with user query"""
    if user_query:
        return (
            PromptTemplate(
                template=REDUCE_SUMMARIZATION_WITH_QUERY,
                input_variables=["input_summaries", "user_query"]
            )
            | ChatWatsonx(**llm_config)
            | StrOutputParser()
        )
    return (
        PromptTemplate(template=REDUCE_SUMMARIZATION, input_variables=["input_summaries"])
        | ChatWatsonx(**llm_config)
        | StrOutputParser()
    )


def get_executive_chain():
    """Get executive summarization chain"""
    return (
        PromptTemplate(template=EXECUTIVE_SUMMARIZATION, input_variables=["input_text"])
        | ChatWatsonx(**llm_config)
        | StrOutputParser()
    )