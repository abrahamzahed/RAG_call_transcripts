# Log the model to MLflow
with mlflow.start_run(run_name=databricks_resources.get("mlflow_run_name")):
    logged_chain_info = mlflow.langchain.log_model(
        lc_model=os.path.join(os.getcwd(), 'rag_chain.py'),  # Chain code file e.g., /path/to/the/rag_chain.py 
        model_config='rag_model_config.yaml',  # Chain configuration 
        artifact_path=databricks_resources.get("artifact_path"),  # Required by MLflow
        input_example=model_config.get("input_example"),  # Save the chain's input schema.  MLflow will execute the chain before logging & capture it's output schema.
    )

# Register the chain to Unity Catalog
uc_registered_model_info = mlflow.register_model(model_uri=logged_chain_info.model_uri, name=model_name_full)
