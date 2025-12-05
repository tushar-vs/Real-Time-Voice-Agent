# ⚡ Nexus: Ultra-Low Latency AI Voice Agent

An industry-grade, real-time voice conversational agent that listens, thinks, and speaks with sub-second latency. Built with Python, FastAPI, and WebSocket streams.

## 🚀 Key Features

- **Full-Duplex Communication:** Listens and speaks simultaneously using WebSocket streams.
- **Interruption Handling:** Instantly stops speaking when the user interrupts (Speech-Started Detection).
- **Sub-Second Latency:** Uses Groq (Llama 3) for inference speeds >800 tokens/sec.
- **State-of-the-Art STT/TTS:** Powered by Deepgram Nova-2 (Speech-to-Text) and Aura (Text-to-Speech).

## 🛠️ Tech Stack

- **Backend:** Python FastAPI (Async WebSockets)
- **Telephony:** Twilio Programmable Voice (Media Streams)
- **Speech-to-Text:** Deepgram Nova-2 (Streaming API)
- **LLM Engine:** Groq (Llama 3 8B)
- **Text-to-Speech:** Deepgram Aura

## 🏗️ Architecture

```mermaid
graph LR
    User[User Phone] <--> Twilio
    Twilio <-->|WebSocket (Audio)| FastAPI[FastAPI Server]
    FastAPI <-->|Stream| Deepgram[STT & TTS]
    FastAPI <-->|JSON| Groq[Llama 3 LLM]
