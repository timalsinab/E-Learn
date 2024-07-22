'''
Adding OpenAI's ChatGPT to allow
users to gain recommendations for
their personal finances.
'''
# Adding local imports
# pip install python-dotenv flask openai sqlite3
from openai import OpenAI
from dotenv import load_dotenv

# Initializing OpenAI client
load_dotenv()
client = OpenAI() # by default, uses os.environ.get("OPENAI_API_KEY") 
                  # to assign api_key to the client variable

# Function to get AI's response
# Assumes user_message is a string input
def get_user_response(user_message):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        max_tokens = 150,
        temperature = 0,
        messages=[
            {"role": "system", "content": "You are an AI tutor that provides detailed explanations and helps students understand complex concepts related to their course material. Answer the user's questions as thoroughly as possible."},
            {"role": "user", "content": user_message}
        ]
    )
    return response.choices[0].message.content