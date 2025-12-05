import os
import json
import base64
import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocketDisconnect
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.getenv("PORT", 5000))

# Initialize clients
deepgram_client = DeepgramClient(DEEPGRAM_API_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)

app = FastAPI()

SYSTEM_PROMPT = (
    "You are a fast, witty, and helpful AI voice assistant named Nexus. "
    "Keep your responses extremely concise (1-2 sentences). "
    "You are conversational and friendly. Do not use markdown."
)

@app.get("/", response_class=HTMLResponse)
async def index():
    return "<h1>Nexus Voice Agent is Running</h1><p>Connect via Twilio Media Streams.</p>"

@app.post("/twiml")
async def twiml_response(request: Request):
    """Twilio requests this endpoint when a call comes in."""
    host = request.headers.get("host")
    return HTMLResponse(content=f"""
    <Response>
        <Connect>
            <Stream url="wss://{host}/media-stream" />
        </Connect>
    </Response>
    """)

@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """Handle the WebSocket connection for the call."""
    await websocket.accept()
    print("Client connected")

    stream_sid = None
    dg_connection = deepgram_client.listen.live.v("1")

    async def send_audio_to_twilio(audio_data):
        """Helper to send audio chunks back to Twilio."""
        if stream_sid:
            payload = base64.b64encode(audio_data).decode("utf-8")
            message = {
                "event": "media",
                "streamSid": stream_sid,
                "media": {"payload": payload}
            }
            await websocket.send_json(message)

    async def generate_response(text):
        """Generate text from Groq and stream audio from Deepgram TTS."""
        print(f"User said: {text}")
        
        try:
            # 1. Get Text Response from Groq (LLM)
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                model="llama3-8b-8192",
                max_tokens=100,
                temperature=0.7,
            )
            response_text = chat_completion.choices[0].message.content
            print(f"AI Response: {response_text}")

            # 2. Convert Text to Audio (TTS)
            # Note: For lowest latency, we use Deepgram's REST API for TTS here.
             env, you  TTS socket.
            options = {"format": "mulaw", "sample_rate": 8000}
            
            # Synthesize audio
            response = deepgram_client.speak.v("1").save(response_text, options)
            
            # Send the audio data to Twilio
            await send_audio_to_twilio(response.to_buffer())

        except Exception as e:
            print(f"Error generating response: {e}")

    # --- Deepgram Event Handlers ---
    def on_message(self, result, **kwargs):
        """Handle speech-to-text results."""
        sentence = result.channel.alternatives[0].transcript
        if len(sentence) == 0:
            return
            
        if result.is_final:
            # When the user finishes a sentence, process it
            asyncio.run_coroutine_threadsafe(generate_response(sentence), loop)

    def on_utterance_end(self, utterance_end, **kwargs):
        """Optional: Handle end of utterance logic if needed."""
        pass

    def on_speech_started(self, speech_started, **kwargs):
        """Interruption Logic: User started speaking while bot was talking."""
        print(">> INTERRUPT DETECTED")
        if stream_sid:
            # Tell Twilio to clear its audio buffer immediately
            clear_msg = {
                "event": "clear",
                "streamSid": stream_sid
            }
            asyncio.run_coroutine_threadsafe(websocket.send_json(clear_msg), loop)

    # Setup Deepgram connection
    dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
    dg_connection.on(LiveTranscriptionEvents.SpeechStarted, on_speech_started)

    options = LiveOptions(
        model="nova-2",
        encoding="mulaw",
        sample_rate=8000,
        interim_results=True,
        utc="speech_started", # Enable interruption detection
        endpointing=300       # 300ms silence = end of turn
    )

    if await dg_connection.start(options) is False:
        print("Failed to start Deepgram connection")
        await websocket.close()
        return

    # Get the current event loop to run async tasks from sync callbacks
    loop = asyncio.get_event_loop()

    try:
        while True:
            # Receive data from Twilio
            message = await websocket.receive_text()
            data = json.loads(message)

            if data['event'] == 'start':
                stream_sid = data['start']['streamSid']
                print(f"Stream started: {stream_sid}")

            elif data['event'] == 'media':
                # Send raw audio to Deepgram
                audio_payload = base64.b64decode(data['media']['payload'])
                dg_connection.send(audio_payload)

            elif data['event'] == 'stop':
                print("Stream stopped")
                break

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await dg_connection.finish()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
