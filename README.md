# 🚗 ParkSmart AI

**AI-Based Smart Parking Recommendation System**

ParkSmart AI is an intelligent parking recommendation system that predicts parking availability and recommends suitable parking locations using Machine Learning, Graph Theory, and shortest-path algorithms. It aims to reduce parking search time, unnecessary driving, and urban traffic congestion.

## 🎯 Objectives

- Predict parking occupancy and estimate available spaces.
- Recommend suitable parking locations based on availability and distance.
- Find efficient routes using graph-based shortest-path algorithms.
- Reduce the time and fuel wasted searching for parking.
- Support sustainable and smarter urban mobility.

## ✨ Key Features

- **Parking Availability Prediction:** Estimate parking occupancy for a selected time.
- **Smart Recommendations:** Rank parking locations using predicted availability and distance.
- **Shortest-Path Navigation:** Apply Dijkstra's algorithm to find efficient routes.
- **Parking Search and Filters:** Find and compare available parking locations.
- **Interactive Map:** Display parking locations and route information.
- **Data-Driven Insights:** Evaluate predictions and recommendation performance.

## 🛠️ Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React.js, Vite |
| Backend | Python, FastAPI |
| Machine Learning | Pandas, scikit-learn |
| Database | MongoDB |
| Graph Algorithms | Graph Theory, Dijkstra's Algorithm |
| Map | Leaflet, OpenStreetMap |

*The technology stack may be updated as development progresses.*

## 🧠 Discrete Mathematics Concepts

This project applies concepts from Discrete Mathematics:

- **Graph Theory:** Represent parking locations and connecting routes as a graph.
- **Shortest-Path Algorithms:** Use Dijkstra's algorithm to find efficient routes.
- **Sets:** Represent and filter collections of parking locations.
- **Relations and Functions:** Model relationships between locations, routes, and parking availability.
- **Optimization:** Rank parking options using availability and distance constraints.

## 🏗️ Project Structure

```text
ParkSmart-AI/
├── frontend/                 # React user interface
├── backend/                  # FastAPI and database integration
├── ml-model/                 # Parking occupancy prediction
├── recommendation-engine/    # Ranking and graph algorithms
├── docs/                     # Documentation and project reports
├── README.md
└── .gitignore
```

## ⚙️ How It Works

1. The user selects a destination and target time.
2. The system retrieves parking information.
3. The ML model estimates parking occupancy.
4. The system calculates estimated free spaces.
5. The recommendation engine filters and ranks parking locations.
6. Graph algorithms determine efficient routes.
7. The frontend displays recommended parking options and relevant route information.

## 📊 Machine Learning Approach

The initial implementation may use a **Random Forest Regressor** to predict parking occupancy.

Model performance will be evaluated using metrics such as Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE), with a simple baseline used for comparison.

**Data limitation:** If simulated or manually collected data is used, the results will be identified accordingly. Predictions from simulated data do not establish real-world accuracy.

## 🌍 Sustainable Development Goal

**SDG 11 — Sustainable Cities and Communities**

ParkSmart AI aims to contribute to more efficient urban mobility by helping users find suitable parking locations and potentially reducing unnecessary driving.

## 👥 Team

This project is being developed collaboratively by a team of four students.

| Role | Responsibility |
|---|---|
| Member 1 | Frontend Development |
| Member 2 | Backend and Database |
| Member 3 | AI/ML Occupancy Prediction |
| Member 4 | Discrete Mathematics and Recommendation Algorithm |

*Add team members' names and GitHub profiles here.*

## 🚀 Project Status

**Status:** In Development

The initial version will focus on a working prototype using available or simulated parking data. Real-time parking integrations and production deployment may be considered in future iterations.

## 📌 Future Enhancements

- Integration with real-time parking data.
- Live occupancy updates.
- Improved prediction using real historical data.
- Additional routing and parking optimization criteria.
- Deployment for public demonstration.

## 📄 License

A license can be added once the project team decides how the code may be used, modified, and distributed.
