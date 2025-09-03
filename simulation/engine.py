import time
from typing import List, Dict
from .models import Lane, Vehicle

class TrafficSignal:
    """
    Represents a traffic signal for a set of lanes.
    
    A signal can be in a 'red' or 'green' state and controls one direction
    of traffic flow in the intersection.
    """
    def __init__(self, lanes: List[Lane], min_green_duration: int = 10):
        """
        Initializes a TrafficSignal.
        
        Args:
            lanes (List[Lane]): The lanes this signal controls.
            min_green_duration (int): The minimum time this signal must stay green.
        """
        self.lanes = lanes
        self.state = 'red'
        self.min_green_duration = min_green_duration
        self.green_start_time = None

    def turn_green(self):
        """Turns the signal green and records the start time."""
        self.state = 'green'
        self.green_start_time = time.time()

    def turn_red(self):
        """Turns the signal red and resets the timer."""
        self.state = 'red'
        self.green_start_time = None

    def is_min_time_passed(self) -> bool:
        """Checks if the minimum green time has elapsed."""
        if self.state == 'green' and self.green_start_time:
            return (time.time() - self.green_start_time) > self.min_green_duration
        return True # If it's red, it's always ok to switch

    def __repr__(self) -> str:
        return f"Signal(lanes={[lane.id for lane in self.lanes]}, state={self.state})"

class Intersection:
    """
    Manages the entire intersection, including all signals and their states.
    
    This class is the central controller for the simulation engine. It holds the
    signals and orchestrates their state changes based on decisions from the AI logic.
    """
    def __init__(self, configuration: Dict[str, List[Lane]]):
        """
        Initializes an Intersection.
        
        Args:
            configuration (Dict[str, List[Lane]]): A dictionary mapping a direction
                                                   (e.g., 'north') to a list of lanes.
        """
        self.signals = {
            direction: TrafficSignal(lanes) 
            for direction, lanes in configuration.items()
        }
        self.active_direction = None
        print(f"Intersection created with directions: {list(self.signals.keys())}")

    def get_lanes_for_direction(self, direction: str) -> List[Lane]:
        """Returns the lanes for a given direction."""
        return self.signals[direction].lanes

    def set_signal_state(self, direction: str, state: str):
        """
        Sets the state for the signal of a specific direction and updates others.
        
        Args:
            direction (str): The direction to change ('north', 'south', etc.).
            state (str): The new state, must be 'green'.
        """
        if state != 'green':
            raise ValueError("Can only set a signal to 'green'; others will turn red.")

        # If the requested signal is already green and min time hasn't passed, do nothing.
        if self.active_direction == direction and not self.signals[direction].is_min_time_passed():
            return
        
        # Turn all other signals red
        for d, signal in self.signals.items():
            if d != direction:
                signal.turn_red()
        
        # Turn the target signal green
        self.signals[direction].turn_green()
        self.active_direction = direction
        # The print statement below is commented out to make the final output cleaner
        # print(f"Intersection Update: Signal for '{direction}' is now GREEN.")
        
    def __repr__(self):
        return f"Intersection(active_direction={self.active_direction}, signals={self.signals})"