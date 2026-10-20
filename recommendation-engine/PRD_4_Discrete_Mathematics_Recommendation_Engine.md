# PRD 4: Discrete Mathematics and Recommendation Engine

## Project
**ParkSmart AI — AI-Based Smart Parking Recommendation System**

## Objective
Recommend suitable parking locations using predicted availability, route distance, and graph algorithms, while documenting the Discrete Mathematics concepts.

## Responsibilities
- Model route connections as a graph.
- Represent intersections and locations as vertices and road connections as weighted edges.
- Implement Dijkstra's algorithm for non-negative edge weights.
- Calculate estimated free spaces from capacity and predicted occupancy.
- Filter candidates using availability and distance constraints.
- Rank suitable candidates with documented rules.
- Return ranked results and recommendation reasons.
- Test graph and ranking edge cases.
- Explain the mathematical model in the project report.

## Proposed Technology
Python, NetworkX or a custom graph implementation, and Pytest.

## Mathematical Model

### Graph Theory
- Vertices: intersections, destination, and parking locations.
- Edges: route connections.
- Weights: distance or another documented non-negative route cost.

### Shortest Path
Use Dijkstra's algorithm to find a shortest path in the defined graph. Document the weight units.

### Availability
If the ML model predicts occupied spaces:

`predicted_free_spaces = total_capacity - predicted_occupied_spaces`

Validate bounds and rounding. If predictions are percentages, document the conversion to counts.

### Recommendation Flow
1. Receive parking candidates and target time.
2. Obtain predicted occupancy.
3. Calculate estimated free spaces.
4. Filter candidates that fail constraints, such as no predicted free spaces or exceeding maximum distance.
5. Calculate route distances.
6. Rank candidates using an agreed rule—for example, availability first and distance as a tie-breaker, or a documented weighted score.
7. Return ranked options with reasons.

Do not use arbitrary ranking weights without documenting their meaning.

## Discrete Mathematics Concepts
- Graphs, vertices, edges, and weighted graphs.
- Dijkstra's algorithm and its non-negative edge-weight assumption.
- Sets for filtering candidate parking locations.
- Relations and functions linking parking, predictions, and routes.
- Constraints and ranking/optimization rules.

## Deliverables
- Graph representation and route calculation.
- Candidate filtering and ranking function.
- Tests for unreachable nodes, missing data, zero availability, and ties.
- Algorithm complexity and mathematics explanation.
- Setup instructions in `recommendation-engine/README.md`.

## Acceptance Criteria
- Shortest paths are correct on test graphs.
- Unreachable destinations are handled safely.
- Ranking uses the shared data contract.
- Availability and distance units are consistent.
- Recommendation reasons match the ranking logic.
- The report accurately explains the Discrete Mathematics connection.

## Dependencies
Backend provides parking data and integration contracts; ML provides predictions; frontend consumes ranked results and explanations.
