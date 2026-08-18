
# 🚢 MISSOURI ARBITER
### The AI Decision Engine for Intelligent Maritime Traffic

> **From vessel traffic to intelligent maritime orchestration.**
>
> Missouri Arbiter is an agentic AI platform that helps maritime operators make safer, faster, and more explainable decisions across complex waterways.

[![AWS](https://img.shields.io/badge/AWS-Bedrock-orange?style=for-the-badge&logo=amazon-aws)](https://aws.amazon.com/bedrock/)
[![CockroachDB](https://img.shields.io/badge/CockroachDB-Cloud-blue?style=for-the-badge&logo=cockroachlabs)](https://www.cockroachlabs.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow?style=for-the-badge&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)](LICENSE)

---

## 🌊 The Problem

Modern maritime traffic management is increasingly complex.

A single vessel movement can depend on:

- Vessel dimensions and draft
- Channel depth and restrictions
- Weather and hydrodynamic conditions
- Tug availability
- Existing vessel reservations
- Traffic conflicts
- Temporary channel closures
- Historical operational knowledge

Traditional systems often provide **data dashboards**.

But maritime operators need something more:

> **A system that can understand the situation, reason across multiple constraints, take action, and explain why.**

That's the problem Missouri Arbiter is designed to solve.

---

# 🚀 Our Solution

**MISSOURI ARBITER** is an agentic AI maritime decision platform.

Instead of forcing an operator to manually inspect multiple systems, Missouri Arbiter brings the operational context together and allows an AI agent to reason through the situation.

### Example

An operator can ask:

> **"Can this vessel safely transit the channel right now?"**

Missouri Arbiter can:

```text
User Request
     ↓
AI Reasoning
     ↓
Vessel Intelligence
     ↓
Channel Constraints
     ↓
Navigation Restrictions
     ↓
Traffic State
     ↓
Tug Availability
     ↓
Historical / Hydrodynamic Memory
     ↓
Decision
     ↓
Reservation + Audit Ledger
````

The result is not simply an answer.

It is an **operational decision backed by live data and traceable actions.**

---

# 🧠 What Makes Missouri Arbiter Different?

Missouri Arbiter is designed around a simple principle:

> **AI should not replace maritime infrastructure — it should intelligently orchestrate it.**

The system combines:

### 🤖 Agentic AI

The AI determines what information it needs and orchestrates the appropriate operational tools.

### 🗄️ CockroachDB

Acts as the persistent operational source of truth for vessels, channels, restrictions, reservations, tug capabilities, hydrodynamic memory, and decisions.

### ☁️ AWS Bedrock

Provides the AI reasoning layer using **Amazon Nova Lite**.

### 🔌 MCP / Tool Orchestration

Allows the agent to interact with real operational capabilities instead of generating disconnected text.

### 📋 Decision Auditability

Important decisions are recorded so operators can understand what happened and why.

---

# ⚓ Core Capabilities

## 1. 🚢 Vessel Intelligence

Retrieve operational specifications including:

* Draft
* Length
* Beam
* Vessel type
* Navigation constraints

The agent uses this information when evaluating transit feasibility.

---

## 2. 🌊 Channel Intelligence

Missouri Arbiter understands:

* Channel depth
* Channel limitations
* Vessel restrictions
* Operational constraints

This allows the agent to evaluate whether a vessel can safely navigate a particular corridor.

---

## 3. 🚧 Dynamic Restrictions

The system can account for changing operational conditions such as:

* Channel closures
* Draft restrictions
* Severe weather hazards
* Temporary navigation constraints

The agent can reconsider its decision when the environment changes.

---

## 4. ⚓ Intelligent Tug Selection

Missouri Arbiter can evaluate available tug capabilities and select appropriate assistance based on operational requirements.

This transforms tug assignment from a manual lookup into an intelligent decision.

---

## 5. 🔄 Intelligent Rerouting

When a preferred route becomes unavailable, Missouri Arbiter can identify alternative channels and reason about the operational consequences.

Example:

```text
Primary Route
     ↓
Restriction Detected
     ↓
Alternative Routes Evaluated
     ↓
Safe Route Selected
     ↓
Operator Decision
```

---

## 6. 🧠 Hydrodynamic Operational Memory

The platform stores operational observations such as:

* Wind conditions
* Current conditions
* Risk scores
* Historical scenarios

This allows the system to incorporate previous operational knowledge into future decisions.

---

## 7. 📋 Decision Ledger

Every important operational action can be recorded.

This creates an auditable history of:

```text
Situation
   ↓
Information Retrieved
   ↓
Reasoning
   ↓
Decision
   ↓
Action
```

This is especially important for safety-critical environments.

---

## 8. 📡 Traffic Simulation

Missouri Arbiter includes a live traffic simulation layer that allows the system to reason about changing vessel conditions and operational states.

This provides a foundation for future real-time maritime traffic management.

---

# 🏗️ Architecture

```text
                       ┌──────────────────────┐
                       │      OPERATOR        │
                       │   Maritime Dashboard │
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │       FASTAPI        │
                       │     API Gateway      │
                       └──────────┬───────────┘
                                  │
                                  ▼
                 ┌────────────────────────────────┐
                 │      MISSOURI ARBITER AGENT    │
                 │                                │
                 │  Reason → Plan → Tool → Decide │
                 └───────────────┬────────────────┘
                                 │
                 ┌───────────────┼────────────────┐
                 │               │                │
                 ▼               ▼                ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │ AWS Bedrock  │ │ MCP / Tools  │ │   Traffic    │
        │ Nova Lite    │ │ Orchestration│ │  Simulator   │
        └──────────────┘ └───────┬──────┘ └──────────────┘
                                 │
                                 ▼
                       ┌──────────────────────┐
                       │    CockroachDB       │
                       │      Cloud           │
                       │                      │
                       │ • Vessels            │
                       │ • Channels           │
                       │ • Restrictions       │
                       │ • Tugs               │
                       │ • Reservations       │
                       │ • Memory             │
                       │ • Decision Ledger    │
                       └──────────────────────┘
```

---

# ☁️ AWS + CockroachDB Integration

These technologies are not simply dependencies.

They form the core of the system.

### AWS Bedrock = Reasoning

Amazon Bedrock provides the intelligence that understands the operator's request, determines which operational information is needed, and orchestrates the decision process.

### CockroachDB = Operational Truth

CockroachDB provides the persistent, transactional state that the AI reasons over.

The interaction looks like:

```text
Operator
   ↓
AWS Bedrock
   ↓
Agent reasoning
   ↓
MCP / Operational Tools
   ↓
CockroachDB
   ↓
Live operational data
   ↓
AWS Bedrock
   ↓
Decision
   ↓
CockroachDB
   ↓
Reservation + Audit Record
```

This makes the architecture significantly more powerful than an AI chatbot connected to static data.

---

# 🔥 Example Scenario

### Situation

A large vessel requests passage through a constrained channel.

### Missouri Arbiter:

**1.** Identifies the vessel.

**2.** Retrieves vessel dimensions and draft.

**3.** Checks channel limitations.

**4.** Checks active restrictions.

**5.** Evaluates current traffic.

**6.** Checks available tug capabilities.

**7.** Retrieves relevant operational memory.

**8.** Determines whether the requested route is feasible.

**9.** If necessary, evaluates alternative routes.

**10.** Creates a reservation when appropriate.

**11.** Records the resulting decision in the audit ledger.

The operator gets a decision rather than having to manually coordinate every subsystem.

---

# 🖥️ Product Experience

Missouri Arbiter provides a mission-control-inspired maritime dashboard designed around operational visibility.

The interface brings together:

* 🚢 Vessel activity
* 🌊 Channel status
* ⚓ Tug availability
* 🚧 Restrictions
* 📡 Traffic simulation
* 🧠 AI decisions
* 📋 Decision history
* 🗄️ Operational data

The goal is to make complex maritime operations understandable at a glance.

---

# 🛠️ Technology Stack

| Layer              | Technology            |
| ------------------ | --------------------- |
| AI Reasoning       | AWS Bedrock           |
| AI Model           | Amazon Nova Lite      |
| Database           | CockroachDB Cloud     |
| Backend            | Python                |
| API                | FastAPI               |
| Database Driver    | Psycopg               |
| Cloud SDK          | Boto3                 |
| Agent Architecture | Agentic AI + MCP      |
| Frontend           | HTML, CSS, JavaScript |
| Deployment         | Render                |
| License            | MIT                   |

---

# 📁 Project Structure

```text
MISSOURI-ARBITER/
│
├── backend/
│   ├── agent/
│   │   ├── arbiter_agent.py
│   │   ├── providers.py
│   │   └── tools.py
│   │
│   ├── db/
│   │   ├── connection.py
│   │   ├── repository.py
│   │   ├── schema.sql
│   │   └── vector_memory.py
│   │
│   ├── simulator/
│   │   └── traffic_sim.py
│   │
│   ├── bedrock_provider.py
│   └── main.py
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── images/
│
├── scripts/
├── tests/
├── docs/
├── requirements.txt
├── LICENSE
└── README.md
```

---

# ⚙️ Running Locally

## 1. Clone

```bash
git clone https://github.com/manohar-jha/Missouri-Arbiter.git
cd Missouri-Arbiter
```

## 2. Create a virtual environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure environment variables

Create a `.env` file:

```env
ARBITER_MODE=CLOUD

DATABASE_URL=YOUR_COCKROACHDB_CONNECTION_STRING

LLM_PROVIDER=bedrock

BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0

AWS_REGION=us-east-1

AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_KEY
```

> ⚠️ Never commit `.env` or cloud credentials to GitHub.

## 5. Start the server

```bash
uvicorn backend.main:app --reload
```

Open:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/health
```

---

# 🧪 Testing

Run the complete test suite:

```bash
python -m pytest
```

The project includes tests covering:

* Agent functionality
* Database operations
* Serialization
* Tool execution
* Core operational workflows

---

# 🌍 Real-World Impact

Missouri Arbiter is designed around a much larger vision.

Today:

```text
River / Channel Operations
```

Tomorrow:

```text
Ports
   ↓
Inland Waterways
   ↓
Canals
   ↓
Coastal Shipping
   ↓
Autonomous Maritime Fleets
   ↓
Global Maritime Traffic Intelligence
```

The same architecture can eventually support intelligent coordination across increasingly complex maritime environments.

---

# 🔮 What's Next?

### 🚀 Real-Time Maritime Data

Integrate live AIS and environmental data feeds.

### 🌦️ Environmental Intelligence

Incorporate:

* Weather
* Wind
* Currents
* Water levels
* Visibility

### 🛰️ Large-Scale Traffic Optimization

Move from individual vessel decisions toward corridor-wide traffic optimization.

### 🤖 Multi-Agent Maritime Operations

Introduce specialized agents for:

* Navigation
* Port operations
* Safety
* Logistics
* Emergency response

### 🌎 Global Maritime Intelligence Layer

Our long-term vision is an AI infrastructure layer capable of helping coordinate maritime traffic across ports, rivers, canals, and shipping corridors worldwide.

---

# 🏆 Why Missouri Arbiter?

Most maritime software answers:

> **"What is happening?"**

Missouri Arbiter aims to answer:

> **"What should happen next — and why?"**

That's the difference between a dashboard and an intelligent decision system.

---

# 👥 Built With

Built with passion during the hackathon by the Missouri Arbiter team.

**AI × Maritime Operations × AWS × CockroachDB × MCP**

---

# 📜 License

This project is licensed under the **MIT License**.

See [LICENSE](LICENSE) for details.

---

# 🔗 Links

### GitHub

[https://github.com/manohar-jha/Missouri-Arbiter](https://github.com/manohar-jha/Missouri-Arbiter)

### Live Demo

https://missouri-arbiter.onrender.com/

---

<div align="center">

## 🚢 MISSOURI ARBITER

### **Making Maritime Traffic Intelligent.**

**Reason. Coordinate. Decide.**

</div>
```
