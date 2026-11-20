# Quantum-Enhanced-Intelligent-QA-Automation-Framework-
Quantum-Enhanced Intelligent QA Automation Framework
An intelligent web application testing platform that combines AI-assisted test-case generation, browser-based test execution, regression analysis, and quantum-inspired optimization to help prioritize which tests should run first.
Quantum implementation note: QAOA is executed using Qiskit Aer simulation in this project. It does not run on physical quantum hardware.

Overview
The platform analyzes a target website, discovers its pages and interactive elements, generates test scenarios, executes those scenarios in a real browser, and stores execution history and results. A QUBO model and QAOA simulation can then be used to prioritize a subset of test cases under a configurable execution budget.

The repository also includes ShopSphere, a sample e-commerce application that can be used as a target for exploring the discovery and regression-testing workflow.
Key Features
- Website discovery: Uses Playwright to inspect reachable websites and discover routes, links, buttons, inputs, and forms.
- AI-assisted test generation: Supports Gemini and OpenAI provider integrations to generate structured test cases grounded in discovered website elements.
- Automated browser execution: Executes test steps using Playwright and records pass/fail/error outcomes, execution duration, browser console messages, and available screenshots.
- Quantum-assisted test prioritization: Builds a QUBO model using test change impact, historical failure rate, coverage, risk, execution efficiency, and redundancy penalties.
- QAOA simulation: Uses Qiskit and Qiskit Aer to sample candidate test selections. Larger test-selection problems use a hybrid approach.
- Regression and version analysis: Includes application-version comparison, execution history, result views, and developer-oriented reports.
- Dashboard: Provides a React-based interface for managing applications, test cases, executions, optimization runs, and results.
Technology Stack
Layer	Technologies
Frontend	React, TypeScript, Vite, Tailwind CSS
Backend	Python, FastAPI, Uvicorn
Browser automation	Playwright
AI integrations	Google Gemini, OpenAI (optional; API key required)
Quantum optimization	Qiskit, Qiskit Aer, QUBO, QAOA
Optimization utilities	NumPy, SciPy
Database	SQLAlchemy, SQLite or PostgreSQL
API documentation	FastAPI / Swagger UI


Repository Structure
QC_Project/
├── QC-Web/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── ai/             # Gemini/OpenAI providers and AI test generation
│   │   │   ├── api/            # FastAPI routes
│   │   │   ├── database/       # SQLAlchemy models and DB configuration
│   │   │   ├── optimizer/      # QUBO builder and QAOA optimizer
│   │   │   ├── schemas/        # API request/response schemas
│   │   │   ├── services/       # Test generation and supporting services
│   │   │   └── test_engine/    # Website discovery and Playwright execution
│   │   └── requirements.txt
│   └── frontend/
│       └── src/                # React + TypeScript dashboard
├── shopsphere/                 # Sample e-commerce application / test target
├── test_qaoa_run.py            # QAOA UI test helper
└── verify_visuals.py           # Dashboard visual verification helper
Getting Started
Prerequisites
- Python 3.10 or later
- Node.js and npm
- Git
- A Chromium browser installed through Playwright
- Optional: Gemini or OpenAI API key for AI-based test generation
- Optional: PostgreSQL database; SQLite can be used for local development
1. Clone the repository
git clone https://github.com/Manaswi1106/Quantum-Enhanced-Intelligent-QA-Automation-Framework-.git
cd Quantum-Enhanced-Intelligent-QA-Automation-Framework-
2. Set up the backend
cd QC-Web/backend

python -m venv .venv
Activate the virtual environment:

Windows (PowerShell):
.venv\Scripts\Activate.ps1
Windows (Git Bash):
source .venv/Scripts/activate
macOS / Linux:
source .venv/bin/activate
Install Python dependencies and the Playwright Chromium browser:
pip install -r requirements.txt
python -m playwright install chromium
Create a .env file inside QC-Web/backend/:
# Local SQLite database (recommended for a quick local setup)
DATABASE_URL=sqlite:///./qc_web.db

# Optional: configure one AI provider for AI-assisted test generation
GEMINI_API_KEY=your_gemini_api_key
# OPENAI_API_KEY=your_openai_api_key
# OPENAI_MODEL=gpt-4o-mini
The application can use SQLite for local development or PostgreSQL by setting DATABASE_URL to a PostgreSQL connection string. Keep real API keys and database credentials private; do not commit .env.

Optional AI provider packages: Install the provider package corresponding to the key you configure if it is not already present in your environment:
pip install google-genai
For OpenAI instead:
pip install openai
Start the backend from the QC-Web/backend/ directory:
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
Backend URL: http://127.0.0.1:8001

Interactive API documentation: http://127.0.0.1:8001/docs
3. Set up the frontend
Open a second terminal at the repository root:
cd QC-Web/frontend
npm install
npm run dev
Frontend URL: http://localhost:5174

The Vite development server proxies /api requests to the backend at http://localhost:8001.
4. Run the sample ShopSphere application (optional)
ShopSphere is a separate sample e-commerce application included as a target for testing.

Open another terminal:
cd shopsphere
npm install
npm run dev
Vite will print the local URL for ShopSphere (normally http://localhost:5173).

Once ShopSphere is running, open the QC dashboard, add/analyze the ShopSphere URL, and use the platform workflow to discover the application and create and execute tests.
Typical Workflow
1. Start the target application that you want to test (ShopSphere or another reachable website).
2. Start the QC backend and frontend.
3. Analyze an application URL from the dashboard. The discovery engine uses Playwright to inspect the website structure and interactive elements.
4. Generate test cases using the configured AI provider, or manage test cases through the platform.
5. Execute tests to run the selected test cases in Chromium through Playwright.
6. Review results and history, including execution statuses, failure information, timing, and available screenshots.
7. Optimize test selection by building the QUBO model and running the QAOA simulation with a selected budget and circuit settings.
8. Compare application versions and review the regression/developer report where applicable.
QUBO Test-Selection Model
Each test case is represented by a binary decision variable:
- 1 — select the test case
- 0 — do not select the test case
The implementation calculates a weighted test value using these default factors:
Factor	Default weight
Change impact	0.30
Historical failure rate	0.20
Coverage	0.20
Risk	0.20
Execution efficiency	0.10


A configurable budget constraint and redundancy penalties are incorporated into the QUBO formulation. The QAOA optimizer uses Qiskit Aer simulation for smaller instances and a hybrid strategy for larger instances.
API Overview
The backend exposes REST endpoints under /api. Important endpoint groups include:
Capability	Endpoint
Analyze a website	POST /api/applications/analyze
List analyzed applications	GET /api/applications
Generate test cases	POST /api/test-cases/generate
List test cases	GET /api/test-cases
Execute tests	POST /api/tests/execute
View execution	GET /api/executions/{execution_id}
View execution history	GET /api/history
View results	GET /api/results
Build QUBO	POST /api/optimization/qubo
Run QAOA	POST /api/optimization/qaoa
Compare versions	POST /api/versions/compare
Check AI provider status	GET /api/ai/status
Developer report	GET /api/reports/developer


For the complete request and response schemas, start the backend and visit /docs.
Development Notes
- The backend initializes database tables at application startup.
- The frontend uses /api by default and the local Vite configuration proxies API requests to port 8001.
- Website discovery and test execution require the target site to be reachable from the machine running the backend.
- AI-assisted generation requires a valid configured provider key. Without one, provider-based generation is unavailable.
- QAOA results are simulator-based; results can vary with circuit depth, shots, optimizer behavior, and problem size.
- Use only websites you own or are authorized to test. Avoid running automated tests against systems without permission.
Security
- Never commit .env files, API keys, database credentials, or other secrets.
- Use environment variables for local and deployment configuration.
- The included ShopSphere payment flow is a demo/mock payment flow, not a real payment processor.
Future Enhancements
Potential directions for extending the project include:
- Running optimization experiments on additional QAOA circuit depths and shot counts.
- Evaluating selected-test quality against baseline selection strategies.
- Adding richer test analytics and visual regression comparisons.
- Expanding supported CI/CD integrations and automated regression triggers.
Author
Manaswi

GitHub: @Manaswi1106
