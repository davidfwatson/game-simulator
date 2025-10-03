# Realistic MLB Game Simulator

## Project Goal

This command-line tool simulates a complete, realistic Major League Baseball game. The primary goal is to create a simulation that is indistinguishable from a real-game play-by-play log, adhering closely to the rules, strategies, and nuances of modern professional baseball.

The simulation moves beyond simple probability, incorporating a pitch-by-pitch at-bat sequence, dynamic pitcher fatigue, and strategic bullpen management to generate a plausible and engaging game narrative.

## Core Features for Realism

To achieve a high level of authenticity, the simulator implements the following key features:

* **Modern MLB Ruleset:** The simulation strictly follows current MLB rules, including:
    * **The Designated Hitter (DH):** Pitchers do not bat; a DH is used in the lineup for both teams.
    * **Extra-Innings "Ghost Runner":** Starting from the 10th inning, each half-inning automatically begins with a runner on second base to mirror modern pace-of-play rules.
* **Pitch-by-Pitch Simulation:** Every at-bat unfolds one pitch at a time. The engine logs the pitch type, location (in or out of the strike zone), and the outcome (ball, called strike, swinging strike, foul, or in-play), providing a granular and realistic play-by-play.
* **Dynamic Bullpen Management:** Starting pitchers operate on a stamina system based on pitch counts. Once fatigued, the simulation's logic makes a strategic pitching change, selecting an appropriate reliever (Long Reliever, Middle Reliever, or Closer) from the bullpen based on the game situation.
* **Detailed Player Attributes:** All players are defined by specific attributes that influence their performance, including:
    * **Batting statistics** for various hit types.
    * **Batter handedness** (Left, Right, or Switch).
    * **Pitcher handedness**, individual **pitch arsenals** (e.g., Fastball, Slider, Curveball), and a **control** rating.
* **Fictional Rosters:** To ensure a unique experience, the simulator uses entirely fictional teams and players, allowing the focus to remain on the quality of the simulation itself.

## How to Run

1.  Ensure you have Python installed.
2.  Save both `baseball_simulator.py` and `teams.py` in the same directory.
3.  Open your terminal or command prompt, navigate to that directory, and run the following command:
    ```
    python baseball_simulator.py
    ```
The simulation will start immediately and print the full game log to the console.

## Technical Design

The project is split into two main files for modularity and ease of customization:

* **`baseball_simulator.py`**: The core simulation engine containing all the game logic, rules, and state management.
* **`teams.py`**: A data file that defines the rosters, player names, positions, and statistical probabilities. You can easily edit this file to create your own custom teams and players without altering the simulation logic.