from databricks import agents
import os
import mlflow

#Import configs from rag_model_config.yaml file
model_config = mlflow.models.ModelConfig(development_config='rag_model_config.yaml')
databricks_resources = model_config.get("databricks_resources")

# Log the model to MLflow
with mlflow.start_run(run_name=databricks_resources.get("mlflow_run_name")):
    logged_chain_info = mlflow.langchain.log_model(
        lc_model=os.path.join(os.getcwd(), '2_rag_chain.py'),  # Chain code file e.g., /path/to/the/2_rag_chain.py 
        model_config='rag_model_config.yaml',  # Chain configuration 
        artifact_path=databricks_resources.get("artifact_path"),  # Required by MLflow
        input_example=model_config.get("input_example"),  # Save the chain's input schema.  MLflow will execute the chain before logging & capture it's output schema.
    )

# Register the chain to Unity Catalog
mlflow.set_registry_uri("databricks-uc")
uc_registered_model_info = mlflow.register_model(model_uri=logged_chain_info.model_uri, name=model_name_full)

instructions_to_reviewer = f"""### Instructions for Testing call transcript Chatbot assistant

1. **Variety of Questions**:
   - Please try a wide range of questions that you anticipate the end users of the application will ask. This helps us ensure the application can handle the expected queries effectively.

2. **Feedback on Answers**:
   - After asking each question, use the feedback widgets provided to review the answer given by the application.
   - If you think the answer is incorrect or could be improved, please use "Edit Answer" to correct it. Your corrections will enable our team to refine the application's accuracy.

3. **Review of Returned Documents**:
   - Carefully review each document that the system returns in response to your question.
   - Use the thumbs up/down feature to indicate whether the document was relevant to the question asked. A thumbs up signifies relevance, while a thumbs down indicates the document was not useful."""

# Deploy to enable the Review APP and create an API endpoint
deployment_info = agents.deploy(model_name=model_name_full, model_version=uc_registered_model_info.version, scale_to_zero=True)

# Add the user-facing instructions to the Review App
agents.set_review_instructions(model_name_full, instructions_to_reviewer)

def wait_for_model_serving_endpoint_to_be_ready(ep_name):
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.serving import EndpointStateReady, EndpointStateConfigUpdate
    import time
    # TODO make the endpoint name as a param
    # Wait for it to be ready
    w = WorkspaceClient()
        state = ""
    for i in range(200):
        state = w.serving_endpoints.get(ep_name).state
        if state.config_update == EndpointStateConfigUpdate.IN_PROGRESS:
            if i % 40 == 0:
                print(f"Waiting for endpoint to deploy {ep_name}. Current state: {state}")
            time.sleep(10)
        elif state.ready == EndpointStateReady.READY:
            print('endpoint ready.')
            return
        else:
            break
    raise Exception(f"Couldn't start the endpoint, timeout, please check your endpoint for more details: {state}")
    
wait_for_model_serving_endpoint_to_be_ready(deployment_info.endpoint_name)
