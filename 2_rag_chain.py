import os
import mlflow
from operator import itemgetter
from databricks.vector_search.client import VectorSearchClient
from langchain_community.chat_models import ChatDatabricks
from langchain_community.vectorstores import DatabricksVectorSearch
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough

## Enable MLflow Tracing
mlflow.langchain.autolog()

#Import configs from rag_model_config.yaml file
model_config = mlflow.models.ModelConfig(development_config='rag_model_config.yaml')
databricks_resources = model_config.get("databricks_resources")
retriever_config = model_config.get("retriever_config")
llm_config = model_config.get("llm_config")


#The following functions will extract the user query string and previous messages
#The user query string will be passed to the chain as the question
#The user query string + the chat history will be passed as the context for the vector search
#The chat history will be passed to the LLM with the vector search results

# Return the string contents of the most recent message from the user
def extract_user_query_string(chat_messages_array):
    return chat_messages_array[-1]["content"]

def extract_previous_messages(chat_messages_array):
    messages = "\n"
    for msg in chat_messages_array[:-1]:
        messages += (msg["role"] + ": " + msg["content"] + "\n")
    return messages

def combine_all_messages_for_vector_search(chat_messages_array):
    return extract_previous_messages(chat_messages_array) + extract_user_query_string(chat_messages_array)

# Connect to the Vector Search Index
vs_client = VectorSearchClient(disable_notice=True)
vs_index = vs_client.get_index(
    endpoint_name=databricks_resources.get("vector_search_endpoint_name"),
    index_name=retriever_config.get("vector_search_index"),
)
vector_search_schema = retriever_config.get("schema")

# Turn the Vector Search index into a LangChain retriever
vector_search_as_retriever = DatabricksVectorSearch(
    vs_index,
    text_column=vector_search_schema.get("chunk_text"),
    columns=[
        vector_search_schema.get("primary_key"),
        vector_search_schema.get("chunk_text")
    ],
).as_retriever(search_kwargs=retriever_config.get("parameters"))

# Enable the RAG Studio Review App to properly display retrieved chunks
# Enable evaluation suite to measure the retriever
mlflow.models.set_retriever_schema(
    primary_key=vector_search_schema.get("primary_key"),
    text_column=vector_search_schema.get("chunk_text")
)

# Method to format the docs returned by the retriever into the prompt
def format_context(docs):
    chunk_template = retriever_config.get("chunk_template")
    chunk_contents = [
        chunk_template.format(
            chunk_text=d.page_content,
        )
        for d in docs
    ]
    return "".join(chunk_contents)

# Prompt Template for generation
prompt = PromptTemplate(
    template=llm_config.get("llm_prompt_template"),
    input_variables=llm_config.get("llm_prompt_template_variables"),
)

# Foundation Models for generation
model = ChatDatabricks(
    endpoint=databricks_resources.get("llm_endpoint_name"),
    extra_params=llm_config.get("llm_parameters"),
)

# RAG Chain
# 1. question
# 2. question + chat history -> vector search -> search results
# 3. question + search results + chat history -> prompt
# 4. prompt -> model
# 5. model -> answer
chain = (
    {
        "question": itemgetter("messages") | RunnableLambda(extract_user_query_string),
        "context": itemgetter("messages") 
            | RunnableLambda(combine_all_messages_for_vector_search)
            | vector_search_as_retriever
            | RunnableLambda(format_context),
        "chat_history": itemgetter("messages") | RunnableLambda(extract_previous_messages)
    }
    | prompt
    | model
    | StrOutputParser()
)

# Tell MLflow logging where to find your chain.
mlflow.models.set_model(model=chain)
