import streamlit as st
import openai
import time
# import os
# from dotenv import load_dotenv

# load_dotenv()

openai.api_key = st.secrets["OPENAI_API_KEY"]
client = openai

assistant_id = "asst_zcaaPlppR78dqY03pjkM7Pzj"

# Initialize session state variables
if "start_chat" not in st.session_state:
    st.session_state.start_chat = False
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "vector_store_id" not in st.session_state:
    st.session_state.vector_store_id = None
if "last_system_instruction" not in st.session_state:
    st.session_state.last_system_instruction = None
if "last_model_choice" not in st.session_state:
    st.session_state.last_model_choice = None

st.title("Yogita Chatbot Using OpenAI Assistant API")

# Sidebar system instruction and model selection
with st.sidebar:
    st.header("System Instruction")
    system_instruction = st.text_area(
        "System Instruction",
        value="You are a chatbot that can answer questions based on the content of a provided PDF document. If the chatbot cannot find the answer in the PDF, it should strictly respond:\n\n**“Sorry, I didn’t understand your question. Do you want to connect with a live agent?”**",
        height=250
    )

    st.header("Choose Model")
    model_choice = st.selectbox("Select model", ["gpt-4o", "gpt-4o-mini"], index=0)

    # PDF Upload
    st.header("Upload PDF")
    pdf_file = st.file_uploader("Upload PDF", type=["pdf"])

    # PDF Remove Option
    if st.session_state.vector_store_id:
        st.button("Remove PDF", on_click=lambda: remove_pdf())


# Function to update assistant configuration with new system instruction and model choice
def update_assistant_config(system_instruction, model_choice):
    # Update assistant's system instruction and model choice
    assistant = client.beta.assistants.update(
        assistant_id=assistant_id,
        instructions=system_instruction,
        model=model_choice,
        tool_resources={"file_search": {"vector_store_ids": [st.session_state.vector_store_id] if st.session_state.vector_store_id else []}}
    )

# Check if system instruction or model choice has changed and update assistant accordingly
if system_instruction != st.session_state.last_system_instruction or model_choice != st.session_state.last_model_choice:
    update_assistant_config(system_instruction, model_choice)
    st.session_state.last_system_instruction = system_instruction
    st.session_state.last_model_choice = model_choice


# Function to handle PDF removal and update assistant
def remove_pdf():
    if st.session_state.vector_store_id:
        # Remove the PDF from vector store
        client.beta.vector_stores.delete(st.session_state.vector_store_id)
        st.session_state.vector_store_id = None
        update_assistant_config(st.session_state.last_system_instruction, st.session_state.last_model_choice)

# Create or update the vector store and upload PDF
if pdf_file is not None:
    # Create vector store
    vector_store = client.beta.vector_stores.create(name="User PDF Vector Store")
    file_streams = [pdf_file]  # Upload the selected PDF file
    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store.id, files=file_streams
    )

    # Poll status
    print(file_batch.status)
    print(file_batch.file_counts)

    # Set the vector store ID
    st.session_state.vector_store_id = vector_store.id
    update_assistant_config(st.session_state.last_system_instruction, st.session_state.last_model_choice)

# Function to get recent assistant message added in thread
def Recent_Assistant_message_added_in_thread(thread_id):
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    for message in messages.data:
        if message.role == "assistant":
            return message.content[0].text.value
    return None

# Start and Exit Chat buttons
col1, col2 = st.columns(2)
with col1:
    start_chat = st.button("Start Chat")
    if start_chat:
        st.session_state.start_chat = True
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id

with col2:
    if st.button("Exit Chat"):
        st.session_state.messages = []
        st.session_state.start_chat = False
        st.session_state.thread_id = None
        st.session_state.vector_store_id = None
        update_assistant_config(st.session_state.last_system_instruction, st.session_state.last_model_choice)
        # click remove_pdf() function
        remove_pdf()


# Chat interface
if st.session_state.start_chat:
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input, until the user enters a message the next part of the code won't run
    if prompt := st.chat_input("Your message..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
    
        # Send user input to the OpenAI Assistant
        message = client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=prompt
        )

        run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=assistant_id,
            tool_choice="required"
        )

        # Wait for the assistant's response
        while run.status != 'completed':
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id,
                run_id=run.id
            )
        
        assistant_response = Recent_Assistant_message_added_in_thread(st.session_state.thread_id)
        with st.chat_message("assistant"):
            st.markdown(assistant_response)
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
