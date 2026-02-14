# 🏎️ My Garage: The Ultimate Asset Management Platform for Collectors

**Track. Value. Manage. Enjoy.**

My Garage is not just a spreadsheet—it's a professional-grade asset management system designed for automotive enthusiasts, horologists, and collectors of all kinds. Whether you have a garage full of Porsches, a safe full of Patek Philippes, or a cellar full of vintage wines, My Garage helps you track your portfolio's financial performance, manage service history, and plan your next big project.

![Portfolio Dashboard](docs/images/dashboard_hero.png)
*(Placeholder: A screenshot of the main dashboard showing total valuation and asset breakdown)*

## 🌟 Why My Garage?

Most collectors rely on messy spreadsheets or disconnected apps. My Garage brings everything together in a unified, self-hosted platform with a focus on **data ownership**, **financial insight**, and **beautiful design**.

### 🚗 Intelligent Vehicle Management
Stop guessing what your car is worth.
*   **AI-Powered Valuations**: Real-time market data integration tracks your vehicle's value against comparable listings.
*   **VIN Decoding**: Automatic spec population using NHTSA data.
*   **"Race Deck" UI**: A dark-mode interface inspired by professional garages, featuring manufacturer-specific typography.

![Vehicle Detail](docs/images/vehicle_detail.png)

### ⌚ The Horology Salon
A dedicated space for your timepiece collection.
*   **Luxury Aesthetic**: A refined, dark-blue and gold theme designed for fine watches.
*   **Detailed Specs**: Track movements, reference numbers, complications, and provenance.
*   **Winder View**: Visualize your collection in a virtual watch box.

![Horology Salon](docs/images/timepieces.png)

### 🍷 Dynamic Collections
Collect anything. Literally anything.
*   **Custom Schemas**: Define your own fields (Vintage, Region, Artist, Edition) using a drag-and-drop builder.
*   **Universal Tracking**: Manage Art, Wine, Sneakers, Rare Books, or Trading Cards with the same power as your vehicles.

### 🔧 Service & Project Management
Never lose a receipt or forget a part number again.
*   **Digital Service History**: Upload receipts, extract data via OCR (coming soon), and categorize maintenance.
*   **Project Kanban Boards**: Plan upgrades and restorations with a Trello-style board. Track parts from "Wishlist" to "Installed".
*   **Cost Tracking**: See exactly how much you've invested vs. current market value.

![Kanban Board](docs/images/kanban.png)

---

## 🛠️ Built for Developers

My Garage is built on a modern, robust stack designed for scalability and extensibility. It's a perfect playground for Python developers.

*   **Backend**: Django 5.2 LTS (Core Logic) + FastAPI (Microservices)
*   **Database**: PostgreSQL (Relational) + MongoDB (Unstructured/Logs)
*   **Async**: Celery + Redis for background tasks (Valuations, OCR)
*   **AI Integration**: Google Gemini for image generation & analysis
*   **Package Management**: Pixi for hermetic environments

## 🚀 Getting Started

We use **pixi** for a zero-headache setup. No virtualenv hell, no missing system libraries.

### Prerequisites
*   [Pixi](https://prefix.dev/) installed.
*   Git.

### Installation

1.  **Clone the repo**
    ```bash
    git clone https://github.com/yourusername/my_garage.git
    cd my_garage
    ```

2.  **Install dependencies**
    ```bash
    pixi install
    ```

3.  **Configure Environment**
    ```bash
    cp .env.example .env
    # Edit .env with your API keys (Marketcheck, Google Gemini, etc.)
    ```

4.  **Start the Engine**
    Run all services (Django, FastAPI, Celery, Mongo, Redis) with one command:
    ```bash
    pixi run start-app
    ```

5.  **Drive**
    Open your browser to `http://localhost:8000`.

## 📸 Gallery

| Vehicle Dashboard | Service Records |
|:---:|:---:|
| ![Garage View](docs/images/garage_view.png) | ![Service History](docs/images/service_history.png) |

| Schema Builder | Mobile View |
|:---:|:---:|
| ![Schema Builder](docs/images/schema_builder.png) | ![Mobile](docs/images/mobile_view.png) |

## 🗺️ Roadmap

*   [x] Vehicle & Timepiece Tracking
*   [x] Dynamic Collection Schemas
*   [x] Kanban Project Management
*   [ ] **AI Receipt OCR**: Automatically extract vendor and cost from photos.
*   [ ] **360° Spin Viewer**: Interactive vehicle exploration.
*   [ ] **Market Intelligence**: Price alerts and detailed depreciation curves.

## 🤝 Contributing

We welcome fellow enthusiasts! Check out `CLAUDE.md` for developer guidelines and `spec.md` for the detailed feature specifications.

---


*Built with ❤️ and ☕
