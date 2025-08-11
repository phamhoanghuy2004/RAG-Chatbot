## How to run
1. Install the packages: pip install -r requirements.txt
2. Run Redis locally with default port 6379
    - First time: docker run -d --name redis -p 6379:6379 redis:<version>
    - Next time: docker start <redis-name>
    - Check the names by "docker ps -a"
3. Turn off cuda accelerator in docling_extract if not used gpu
4. cmd: "python manage.py runserver" to run django server

## Potential Features

These are improvements considered for future versions of the RAG Chatbot:

1. **Fix Upload Error Message**
    - Uploaded successfully but still shows an error message.
21. **Conversation Memory**
    - Enable the chatbot to remember previous user messages and maintain context across multiple turns.
    - Potential implementation: store chat history in Redis or a database and inject it into prompts.

3. **Improve Upload Time**
    - Optimize the document upload process to handle files faster.
    - Possible approaches:

