# AI-First CRM HCP Module – Log Interaction Screen

## Project Overview

This project is an AI-powered Customer Relationship Management (CRM) system focused on Healthcare Professionals (HCPs). It allows field representatives to log and manage interactions using either a traditional form or an AI-powered conversational chat interface.

The application uses LangGraph agents and Groq LLM to automate interaction logging, summarization, entity extraction, editing, and other CRM-related workflows.

---

## Features

### Log Interaction
- Log meetings with Healthcare Professionals.
- Supports:
  - Structured Form
  - AI Chat Interface
- Automatically generates interaction summaries.
- Extracts important entities such as:
  - Doctor Name
  - Hospital
  - Products Discussed
  - Follow-up Date
  - Action Items

### Edit Interaction
- Modify previously logged interactions.
- AI updates summaries and extracted entities automatically.

### AI Agent (LangGraph)

The LangGraph Agent coordinates all CRM workflows and invokes different tools based on user requests.

### Implemented Tools

1. Log Interaction
2. Edit Interaction
3. Search HCP
4. Generate Follow-up Recommendations
5. Interaction Summary Generator

---

# Tech Stack

## Frontend
- React
- Redux Toolkit
- React Router
- Axios
- Google Inter Font

## Backend

- Python
- FastAPI
- LangGraph
- LangChain
- Groq API

## Database

- PostgreSQL (or MySQL)

## LLM

- Groq
- gemma2-9b-it

---

# Project Structure

```
project-root/

│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── backend/
│   ├── app/
│   ├── agents/
│   ├── tools/
│   ├── routes/
│   ├── models/
│   ├── database/
│   └── main.py
│
├── README.md
└── requirements.txt
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/yourusername/ai-first-crm-hcp.git

cd ai-first-crm-hcp
```

---

## Backend Setup

Create virtual environment

```bash
python -m venv venv
```

Activate environment

Windows

```bash
venv\Scripts\activate
```

Linux/Mac

```bash
source venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run backend

```bash
uvicorn main:app --reload
```

Backend runs on

```
http://localhost:8000
```

---

## Frontend Setup

```bash
cd frontend

npm install

npm run dev
```

Frontend runs on

```
http://localhost:5173
```

---

# Environment Variables

Create a `.env` file inside backend.

```
GROQ_API_KEY=your_groq_api_key

DATABASE_URL=your_database_url
```

---

# LangGraph Workflow

```
User

↓

LangGraph Agent

↓

Intent Detection

↓

Tool Selection

↓

LLM Processing

↓

Database

↓

Response to User
```

---

# API Endpoints

### POST

```
/log-interaction
```

Logs a new HCP interaction.

---

### PUT

```
/edit-interaction/{id}
```

Updates an existing interaction.

---

### GET

```
/interactions
```

Returns all interactions.

---

### GET

```
/interaction/{id}
```

Returns a single interaction.

---

# AI Capabilities

- Natural language interaction logging
- Automatic meeting summarization
- Entity extraction
- Follow-up recommendations
- Editable AI-generated notes

---

# Screens Included

- Dashboard
- Log Interaction Form
- AI Chat Interface
- Interaction History
- Edit Interaction Screen

---

# Future Improvements

- Voice-to-text logging
- OCR for visiting cards
- Calendar integration
- Email reminders
- Analytics Dashboard
- Multi-language support

---

# Assignment Requirements Covered

✔ React UI

✔ Redux State Management

✔ FastAPI Backend

✔ LangGraph Agent

✔ Groq LLM (gemma2-9b-it)

✔ PostgreSQL / MySQL

✔ Log Interaction Tool

✔ Edit Interaction Tool

✔ Additional AI Tools

✔ GitHub Repository

✔ README Documentation

---

# Author

**Rajat Yadav**
