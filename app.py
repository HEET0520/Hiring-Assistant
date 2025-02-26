import streamlit as st
import os
from chatbot import HiringAssistant
from dotenv import load_dotenv
import asyncio
from async_timeout import timeout

# Load environment variables
load_dotenv()
st.set_page_config(layout="wide")
# Custom CSS for better UI
st.markdown("""
    <style>
    /* Full page background */
        .stApp {
            background: #3A0066;
            color: white !important;
        }

        /* Chat input box */
        textarea {
            background: linear-gradient(to right, #4B0082,#000000) !important;
            color: white !important;
            border-radius: 10px !important;
            padding: 10px !important;
        }

        /* Placeholder text inside input box */
        textarea::placeholder {
            color: rgba(255, 255, 255, 0.9) !important; /* Light white */
        }

        /* Arrow button inside chat input */
        button[kind="primary"] {
            background-color: rgba(255, 255, 255, 0.9) !important; /* Light white */
            color: white !important;
            border-radius: 50% !important;
            padding: 8px !important;
        }

        /* On hover, make arrow slightly brighter */
        button[kind="primary"]:hover {
            background-color: rgba(255, 255, 255, 1) !important;
        }

        /* Chat message background */
        .stChatMessage {
            background: linear-gradient(to right, #0f172a, #3b82f6) !important;
            color: white !important;
            border-radius: 10px !important;
            padding: 10px !important;
        }

        /* Sidebar background */
        .css-1d391kg {
            background: linear-gradient(to right, #0f172a, #3b82f6) !important;
        }
        .main-container {
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0px 0px 10px rgba(0,0,0,0.1);
        }
        /* Chat input box */

        /* Placeholder text */
        textarea::placeholder {
            color: rgba(255, 255, 255, 0.9) !important; /* Brighter White */
            font-weight: bold;
        }

        /* Arrow button */
        button[kind="primary"] {
            background-color: rgba(255, 255, 255, 0.6) !important; /* Light white */
            color: #152347 !important; /* Dark Blue Arrow */
            border-radius: 50% !important;
            padding: 8px !important;
        }

        /* Arrow button on hover */
        button[kind="primary"]:hover {
            background-color: rgba(255, 255, 255, 0.8) !important; /* Brighter on hover */
            color: black !important;
        }
        .chat-container {
            display: flex;
            flex-direction: column;
            gap: 12px;
            max-width: 100%;
            margin: auto;
            padding: 20px;
        }

        .user-msg, .assistant-msg {
            display: flex;
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
            max-width: 40%;
            margin-bottom: 10px;
        }

        .user-msg {
            justify-content: flex-end;
            background-color: #4B0082;
            color: white;
            align-self: flex-end;
            text-align: right;
            margin-left: auto;
            margin-bottom: 10px;
        }

        .assistant-msg {
            justify-content: flex-start;
            background-color: #f1f1f1;
            color: #333;
            align-self: flex-start;
            text-align: left;
            margin-right: auto;
            margin-bottom: 10px;
        }

        .title {
            color: #2c3e50;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'hiring_assistant' not in st.session_state:
        api_key = st.secrets['GOOGLE_API_KEY']
        if not api_key:
            st.error("Google API Key not found in secrets")
            st.stop()
        st.session_state.hiring_assistant = HiringAssistant(api_key)
    if 'conversation_ended' not in st.session_state:
        st.session_state.conversation_ended = False

# Display chat messages
def display_chat_history():
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div class="chat-container user-msg">{message["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-container assistant-msg">{message["content"]}</div>', unsafe_allow_html=True)

# Handle user input
async def handle_user_input(user_input: str):
    st.session_state.messages.append({"role": "user", "content": user_input})

    try:
        async with timeout(30):
            response, end_conversation = await st.session_state.hiring_assistant.process_input(user_input)
            st.session_state.messages.append({"role": "assistant", "content": response})

            if end_conversation:
                st.session_state.conversation_ended = True
    except asyncio.TimeoutError:
        st.error("The request timed out. Please try again.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

    st.rerun()

# Main UI
def main():
    st.markdown("<h1 class='title'><i>RecruitX</i></h1>", unsafe_allow_html=True)
    st.markdown("""<h3 class='title'>Welcome to RecruitX's automated hiring assistant! </h3> """, unsafe_allow_html=True)
    st.markdown("""Our AI-driven assistant will guide you through an interactive interview, collecting your details and assessing your responses. Once completed, our team will review your application and get in touch if you're a good fit! <br>
    Type <b>'Hello'</b> to begin your interview.""", unsafe_allow_html=True)

    

    initialize_session_state()
    display_chat_history()

    if st.session_state.conversation_ended:
        st.success("✅ Thank you for participating in the interview! Our team will review your responses and contact you if you're a good fit.")
    else:
        user_input = st.chat_input("Type your response here...")
        if user_input:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(handle_user_input(user_input))
            finally:
                loop.close()
            st.rerun()

if __name__ == "__main__":
    main()
