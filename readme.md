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

1. Conversation memory
2. Logout
3. Selecting document type before upload
4. Enforce picking document before chat
5. Detailed logging