import os
import json
import base64

import openai

from functools import wraps

from bottle import Bottle, request, response, run, template


# Initialize the Bottle app
app = Bottle()

# Replace this with your OpenAI API key
client = openai.OpenAI()

SYSTEM_PROMPT = """
You are a business analyst at one of the top 4 consulting firms. Build a presentation with the specified title and additional context provided.

Here are the conventions to follow:
* Keep the presentation under 7 slides.
* Each slide may not contain more than 7 lines.
* Each line may not be more than 7 words.
* The transcript doesn't have to follow the above rules.

Output the presentation in the following format:

## Slide <slide-number>

<Slide Content>

### Transcript

<Slide Transcript>

-- End of Slide <slide-number>"""

MODEL = "gpt-4-1106-preview"


def csrf_protect(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        request_csrf_token = request.get_cookie('csrf_token')
        if not request_csrf_token or request_csrf_token != request.POST.get('csrf_token'):
            return {'error': 'Invalid CSRF token.'}
        return f(*args, **kwargs)
    return decorated_function


def generate_csrf_token():
    return base64.b64encode(os.urandom(32)).decode('utf-8')


@app.get('/')
def index():
    # Generate a CSRF token
    csrf_token = generate_csrf_token()

    # Set the CSRF token as a cookie in the response
    response.set_cookie('csrf_token', csrf_token, httponly=True)

    # Render the HTML page with the CSRF token in it (optional)
    return template(
        open('templates/index.html').read(),
        csrf_token=csrf_token,
        system_prompt=SYSTEM_PROMPT,
        model=MODEL
    )


@app.post('/')
@csrf_protect
def generate_ppt():
    # Get the prompt from the POST request
    data = request.POST
    system_prompt = data.get('system_prompt')
    prompt = data.get('prompt')

    if not prompt:
        return {'error': 'No prompt provided'}

    user_content = f"Title: {prompt}"
    context = data.get('context')
    if context:
        user_content += f'\nContext: {context}'
    try:
        # Making a call to OpenAI's ChatGPT
        openai_response = client.chat.completions.create(
            model=data.get('model'),  # Or whichever model you prefer
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )

        # Extract the text from the response
        gpt_output = openai_response.choices[0].message.content

        # Return the output as JSON
        return json.dumps({"response": gpt_output})

    except Exception as e:
        response.status = 500
        return {'error': str(e)}


if __name__ == '__main__':
    run(app, host='localhost', port=8080)
