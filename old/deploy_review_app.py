import agents
import mlflow

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

wait_for_model_serving_endpoint_to_be_ready(deployment_info.endpoint_name)
