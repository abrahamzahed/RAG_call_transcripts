#Create the endpoint
client = VectorSearchClient(service_principal_client_id=,service_principal_client_secret=)

client.create_endpoint(
    name=databricks_resources.get("vector_search_endpoint_name"),
    endpoint_type="STANDARD"
)

#Generate a sample dataset of customer support call transcripts and write them to a delta table
transcripts = [
    (1, "Customer: Hi, I'm having trouble with my data plan. It seems to be running out faster than usual. Agent: I understand your concern. Let's take a look at your account and usage patterns to identify any issues."),
    (2, "Customer: Hello, I'd like to upgrade my phone. Can you tell me what options are available? Agent: Certainly! I'd be happy to go over our current phone upgrade options with you. What type of phone are you interested in?"),
    (3, "Customer: I'm getting poor signal at my new house. Is there anything that can be done? Agent: I'm sorry to hear that. Let's check the coverage in your area and see if there are any network improvements planned. Can you provide me with your new address?"),
    (4, "Customer: My bill seems higher than usual this month. Can you explain why? Agent: Of course, I'd be glad to review your bill with you. Let's go through the charges together and I'll explain any changes or additional fees."),
    (5, "Customer: I'm traveling abroad next week. How can I use my phone internationally? Agent: Great question! I can help you set up an international plan for your trip. First, let me know which countries you'll be visiting and for how long.")
]

transcripts_df = spark.createDataFrame(data, ["id", "call_transcript"])

(transcripts_df.write
  .format("delta")
  .mode("overwrite")
  .saveAsTable(databricks_resources.get("source_delta_table")))

#Create the vector search index
#Use a delta sync index with a CONTINUOUS pipeline type so the index will be updated automatically when new records are added to the delta table
index = client.create_delta_sync_index(
  endpoint_name=databricks_resources.get("vector_search_endpoint_name"),
  source_table_name=databricks_resources.get("source_delta_table"),
  index_name=retriever_config.get("vector_search_index"),
  pipeline_type="CONTINUOUS", #update the index anytime the source table changes
  primary_key=retriever_config.get("schema").get("primary_key"),
  embedding_source_column=retriever_config.get("schema").get("chunk_text"),
  embedding_model_endpoint_name=databricks_resources.get("embedding_model_endpoint_name")
)
