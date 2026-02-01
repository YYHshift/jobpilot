# ✈️ JobPilot - AI-Powered Job Market Intelligence

![Project Status](https://img.shields.io/badge/Status-Active-success)
![License](https://img.shields.io/badge/License-MIT-blue)

**JobPilot** is a full-stack application that transforms unstructured job posting data into actionable market intelligence. By leveraging **Google Gemini (LLM)**, it automatically scrapes, parses, and visualizes job trends from Seek.com.au, helping job seekers understand skill demands, salary distributions, and hiring hotspots.

> **Live Demo:** [Click here to view the Analytics Dashboard](https://jobpilot-h1ih.vercel.app/)  
> *(Note: The crawler engine runs locally for performance, while the dashboard is hosted on Vercel.)*

---

## ✨ Key Features

* **🤖 AI-Driven Parsing**: Uses **Google Gemini 1.5 Flash** to extract structured data (Skills, Salary, Seniority, Tech Stack) from complex job descriptions.
* **📊 Interactive Dashboard**: A React-based analytics suite featuring:
    * **Skill Heatmaps**: Top in-demand technologies.
    * **Salary Distribution**: Normalized salary ranges.
    * **Geographic Analysis**: Hiring hotspots across Australia.
    * **Work Type Breakdown**: Contract vs. Full-time ratios.
* **⚡ Hybrid Architecture**: Designed with a "Local Ingestion, Cloud Presentation" pattern to optimize for heavy scraping workloads while maintaining high availability for data consumption.
* **🛡️ Robust Backend**: FastAPI service with Supabase (PostgreSQL) integration for reliable data persistence.

---

## 🛠️ Tech Stack

### Frontend
* **Framework**: [Next.js 14](https://nextjs.org/) (App Router)
* **Language**: TypeScript
* **Styling**: Tailwind CSS
* **Visualization**: Recharts
* **Deployment**: Vercel

### Backend & Data
* **API Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
* **Scraping**: Selenium WebDriver (Chrome)
* **AI Model**: Google Gemini API
* **Database**: Supabase (PostgreSQL)
* **Deployment**: Render (Web Service)

---

## 🏗️ Architecture

JobPilot employs a **Separation of Concerns** principle:

1.  **Data Ingestion Layer (Local)**:
    * Runs `scraper.py` locally to bypass cloud environment restrictions (e.g., memory limits for Headless Chrome).
    * Raw HTML is processed, sent to Gemini for extraction, and saved to Supabase.
2.  **API Layer (Cloud - Render)**:
    * Host the REST API endpoints.
    * Handles data retrieval, aggregation, and statistical calculations.
3.  **Presentation Layer (Cloud - Vercel)**:
    * Consumes the API to render real-time charts and insights.

---

## 🚀 Getting Started

To run the full stack (Crawler + Dashboard) locally, follow these steps:

### 1. Prerequisites
* Python 3.10+
* Node.js 18+
* Google Chrome (for scraping)

### 2. Backend Setup
```bash
cd backend
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup Environment Variables
# Create a .env file in /backend with:
# GOOGLE_API_KEY=your_key
# SUPABASE_URL=your_url
# SUPABASE_KEY=your_key

# Run the Server
uvicorn main:app --reload

```

### 3. Frontend Setup

```bash
cd frontend
# Install dependencies
npm install

# Run the Development Server
npm run dev

```

Open [http://localhost:3000](https://www.google.com/search?q=http://localhost:3000) to view the app.

---

## 🔮 Future Improvements

* [ ] **Cron Job Integration**: Automate daily scraping using GitHub Actions or Airflow.
* [ ] **Resume Matcher**: Upload a PDF resume to get a "Match Score" against job listings using RAG.
* [ ] **User Auth**: Allow users to save favorite jobs and track application status.

---

## 👨‍💻 Author

**Yuhe (Stewie) Yang**

* [GitHub](https://www.google.com/search?q=https://github.com/YYHshift)
* [LinkedIn](https://www.google.com/search?q=https://linkedin.com/in/stewieyang)
* [Portfolio](https://www.google.com/search?q=https://yuheyang.vercel.app)

*Built with ❤️ in Perth, WA.*
