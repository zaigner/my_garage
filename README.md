# My Garage: The Ultimate Asset Management Platform for Collectors

**Track. Value. Manage. Enjoy.**

![Python](https://img.shields.io/badge/python-3.12-blue)
![Django](https://img.shields.io/badge/django-5.2_LTS-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

My Garage is not just a spreadsheet — it's a professional-grade, **self-hosted** asset management system for automotive enthusiasts, horologists, and collectors of all kinds. Whether you have a garage full of Porsches, a safe full of Patek Philippes, or a cellar full of vintage wines, My Garage tracks your portfolio's financial performance, manages service history, and plans your next big project.

**Own Your Data.** No subscriptions. No third-party accounts. Your collection, your server, your rules.

**What it does:**
- Tracks vehicles, watches, and any custom collection in one place
- Pulls real market data to keep your valuations current
- Manages service history, project kanban boards, and cost tracking
- Runs entirely on your own hardware

---

## Why My Garage?

Most collectors rely on messy spreadsheets or disconnected apps. My Garage brings everything together in a unified, self-hosted platform with a focus on **data ownership**, **financial insight**, and **beautiful design**.

### Intelligent Vehicle Management
Stop guessing what your car is worth.
- **Automated Valuations**: Real-time market data integration tracks your vehicle's value against comparable listings.
- **VIN Decoding**: Automatic spec population using NHTSA data.
- **"Race Deck" UI**: A dark-mode interface inspired by professional garages, featuring manufacturer-specific typography.

### The Horology Salon
A dedicated space for your timepiece collection.
- **Luxury Aesthetic**: A refined, dark-blue and gold theme designed for fine watches.
- **Detailed Specs**: Track movements, reference numbers, complications, and provenance.
- **Winder View**: Visualize your collection in a virtual watch box.

### Dynamic Collections
Collect anything. Literally anything.
- **Custom Schemas**: Define your own fields (Vintage, Region, Artist, Edition) using a drag-and-drop builder.
- **Universal Tracking**: Manage Art, Wine, Sneakers, Rare Books, or Trading Cards with the same power as your vehicles.

### Service & Project Management
Never lose a receipt or forget a part number again.
- **Digital Service History**: Upload receipts, extract data via OCR, and categorize maintenance automatically.
- **Project Kanban Boards**: Plan upgrades and restorations with a Trello-style board. Track parts from "Wishlist" to "Installed".
- **Cost Tracking**: See exactly how much you've invested vs. current market value.

### AI-Powered Intelligence
- **Smart Valuations**: Pulls real market comps and assembles AI context to estimate what your asset is worth today.
- **Receipt OCR**: Photograph a service receipt — vendor, date, cost, and line items are extracted automatically.
- **Condition Grading**: Upload photos of any area; AI grades condition (1–10) and estimates value impact on your portfolio.
- **Instant Descriptions**: Generate rich, accurate item descriptions from structured data.
- **Claude Code Integration**: Full MCP server — query your garage, look up valuations, and enrich asset data directly from Claude Code.

---

## Built for Developers

My Garage is built on a modern, robust stack designed for scalability and extensibility.

- **Backend**: Django 5.2 LTS (Core Logic) + FastAPI (Microservices & MCP Server)
- **Database**: PostgreSQL (Relational) + MongoDB (Embeddings, RAG, AI Traces)
- **Async**: Celery + Redis for background tasks (Valuations, OCR)
- **AI**: Google Gemini for embeddings, image generation & analysis; RAG knowledge layer over your own docs
- **Package Management**: Pixi for hermetic, reproducible environments

## Getting Started

We use **pixi** for a zero-headache setup. No virtualenv hell, no missing system libraries.

### Prerequisites
- [Pixi](https://prefix.dev/) installed
- Git

### Installation

1. **Clone the repo**
    ```bash
    git clone https://github.com/yourusername/my_garage.git
    cd my_garage
    ```

2. **Install dependencies**
    ```bash
    pixi install
    ```

3. **Configure Environment**
    ```bash
    cp .env.example .env
    # Edit .env with your API keys (Marketcheck, Google Gemini, etc.)
    ```

4. **Start the Engine**
    Run all services (Django, FastAPI, Celery, Mongo, Redis) with one command:
    ```bash
    pixi run start-app
    ```

5. **Drive**
    Open your browser to `http://localhost:8000`.

---

## Roadmap

- [x] Vehicle & Timepiece Tracking
- [x] Dynamic Collection Schemas
- [x] Kanban Project Management
- [x] Receipt OCR — extract vendor and cost from service receipt photos
- [x] Watch Valuation — estimated values via brand, condition, and completeness
- [ ] **360° Spin Viewer**: Interactive vehicle exploration
- [ ] **Market Intelligence**: Price alerts and detailed depreciation curves
- [ ] **WatchCharts Integration**: Live secondary market data for timepieces

## Contributing

This is a personal project in active development — issues and ideas welcome. If you want to contribute, open an issue to discuss first.

---

*Built with ADHD*
