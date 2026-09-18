from datetime import date
from enum import Enum
from typing import TypedDict, Optional
from uuid import uuid4

from pydantic import BaseModel, model_validator
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama

from application import (
    Status,
    create_application,
    update_status_by_id,
    get_last_matching_application_id,
)
from gmail_client import get_last_n_emails
from db import EmailRepository

BLACKLISTED_EMAILS = [
    "jobalerts-noreply@linkedin.com"
]

class EmailType(str, Enum):
    APPLICATION = "application"
    REJECTION = "rejection"

class CompanyData(BaseModel):
    company_name: Optional[str]
    role: Optional[str]
    is_job_email: bool
    type: Optional[EmailType]

    @model_validator(mode="after")
    def validate_data(self):
        if not self.is_job_email:
            self.company_name = None
            self.role = None
            self.type = None
        return self

model = ChatOllama(
    model = "gemma3:12b",
    temperature = 0
)

structured_model = model.with_structured_output(CompanyData)

class AgentState(TypedDict):
    email: str
    id: str
    date: str
    extracted_data: Optional[CompanyData]
    update_row_id: Optional[str]

def extract_email_data(state: AgentState):

    email = state["email"]

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
You are a strict job application email classifier.

Your ONLY task is to determine whether the email is about a JOB APPLICATION THAT THE USER HAS ALREADY SUBMITTED.

IMPORTANT:
An email mentioning a job, job title, company, hiring, or an opportunity does NOT automatically mean it is a job application email.

CLASSIFY AS NOT A JOB EMAIL (is_job_email=false) if the email is:
- A LinkedIn job alert
- A LinkedIn recommended jobs email
- A job search notification
- A list of available jobs
- A job advertisement
- A "jobs you may be interested in" email
- A recruiter contacting the user about a job when there is no evidence of an existing application
- A company advertising an open position
- A career newsletter
- A hiring newsletter
- A general recruiting email
- Any email where the user has NOT clearly already applied

For these emails, return:
{{
    "company_name": null,
    "role": null,
    "type": null,
    "is_job_email": false
}}

CLASSIFY AS A JOB EMAIL (is_job_email=true) ONLY if the email clearly refers to an application that has already been submitted.

Examples:
- "We received your application for Software Engineer."
- "Thank you for applying to Acme."
- "Your application for Software Engineer is under review."
- "We have decided not to move forward with your application."
- "Unfortunately, your application has been rejected."
- "Your application has been submitted successfully."

For these emails:

APPLICATION:
Use type="application" when the email confirms, acknowledges, or provides a status update about an application.

REJECTION:
Use type="rejection" when the email clearly rejects an application or says the company will not proceed with the candidate's application.

REJECTION HAS PRIORITY:
If an email both refers to an application and communicates a rejection, use type="rejection".

EXTRACTION:

company_name:
Extract the company associated with the existing application.
Do not guess.
If it cannot be determined, use null.

role:
Extract the job title associated with the existing application.
If the role is not mentioned, use null.
Do not guess.

FINAL RULE:
When in doubt about whether the email concerns an existing application, classify it as NOT A JOB EMAIL.

Return ONLY the structured output.
"""
        ),
        (
            "human",
            "{email}"
        )
    ])

    chain = prompt | structured_model

    response = chain.invoke({
        "email": email
    })

    print("\nLLAMA RESPONSE:")
    print(response)


    return {
        "extracted_data": response
    }

def is_job_email(state: AgentState):
    extracted_data = state.get("extracted_data")

    if extracted_data is None:
        return "no"

    if not extracted_data.is_job_email:
        return "no"

    return "yes"

def handle_application(state: AgentState):
    extracted_data = state.get("extracted_data")

    if extracted_data is None:
        return state

    company_name = extracted_data.company_name
    role_name = extracted_data.role
    email_type = extracted_data.type

    if email_type == EmailType.APPLICATION:
        new_id = state.get("id")
        create_application(
            application_id=new_id,
            application_date=state.get("date"),
            company_name=company_name,
            role_name=role_name,
            status=Status.APPLIED,
        )
        state["update_row_id"] = new_id

    elif email_type == EmailType.REJECTION:
        existing_id = get_last_matching_application_id(
            company_name,
            role_name,
        )

        if existing_id:
            update_status_by_id(existing_id, Status.REJECTED)
            state["update_row_id"] = existing_id

    return state

graph_builder = StateGraph(AgentState)
graph_builder.add_node("extract_email_data", extract_email_data)
graph_builder.add_node("handle_application", handle_application)
graph_builder.add_edge(START, "extract_email_data")
graph_builder.add_conditional_edges("extract_email_data", is_job_email, {
    "yes": "handle_application",
    "no": END
})
graph_builder.add_edge("handle_application", END)
graph = graph_builder.compile()

email_repository = EmailRepository()
emails = get_last_n_emails(50)
emails.reverse()

for email in emails:
    if any(blacklisted in email["From"] for blacklisted in BLACKLISTED_EMAILS):
        continue
    if email_repository.is_processed(email["ID"]):
        continue
    state = {
        "email": email["Body"],
        "id": email["ID"],
        "date": email["Date"],
        "extracted_data": None,
        "update_row_id": None
    }
    graph.invoke(state)
    email_repository.mark_processed(email["ID"])