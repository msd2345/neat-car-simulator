# NEAT Car Simulator

A self-driving car simulation built with Python and Pygame, using the NEAT algorithm (Neuro Evolution of Augmenting Topologies) to train neural networks through genetic evolution.

## How It Works

Each car is controlled by its own neural network that takes sensor inputs from the environment and outputs steering decisions. No rules are hardcoded — the cars learn entirely on their own through evolution.

Over successive generations:
- The fittest networks survive and pass their traits forward
- Cars get progressively better at navigating the track
- Eventually they can complete complex tracks entirely autonomously

## Features

- Neural networks evolve in real time through genetic evolution
- Cars learn to navigate tracks with no hardcoded rules
- Custom map builder — design your own tracks and watch networks adapt from scratch
- Visual simulation showing all cars and their sensors in real time

## Technologies Used

- Python
- Pygame
- NEAT-Python

## Installation & Setup

1. Clone the repository
   git clone https://github.com/msd2345/neat-car-simulator.git

2. Install dependencies
   pip install pygame neat-python

3. Run the simulation
   python main.py

## Project Structure

Assets/       — Track images and visual assets
config.txt    — NEAT algorithm configuration
main.py       — Main simulation file
