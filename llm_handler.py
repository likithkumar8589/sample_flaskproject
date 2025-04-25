from ollama import Client

# Initialize Ollama client
ollama_client = Client(host='http://localhost:11434')

def generate_response(prompt):
    try:
        response = ollama_client.chat(
            model="mistral",
            messages=[{"role": "user", "content": prompt}]
        )
        return response['message']['content']
    except Exception as e:
        return f"⚠️ Error generating response: {str(e)}"
