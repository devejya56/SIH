# main.py

import time
import random
import threading

# Import our custom modules from the 'simulation' package
from simulation.models import Lane, Vehicle
from simulation.engine import Intersection
from simulation.logic import DynamicPriorityLogic

# --- Simulation Configuration ---
SIMULATION_DURATION_SECONDS = 180  # How long each simulation run should last in virtual seconds
VEHICLE_SPAWN_PROBABILITY = 0.4   # Chance of a new vehicle appearing on a lane each second
CARS_PER_SECOND_GREEN_LIGHT = 1   # How many cars pass a green light each second

class Simulation:
    """
    Orchestrates a complete traffic simulation run.
    """
    def __init__(self, logic_mode: str):
        """
        Initializes the simulation.
        
        Args:
            logic_mode (str): The logic to use for traffic signals. 
                              Can be 'dumb' for fixed-timer or 'ai' for dynamic logic.
        """
        if logic_mode not in ['dumb', 'ai']:
            raise ValueError("logic_mode must be 'dumb' or 'ai'")
            
        self.logic_mode = logic_mode
        self.intersection = self._setup_intersection()
        self.ai_logic = DynamicPriorityLogic(car_weight=1.0, wait_time_weight=0.5)
        
        # For the 'dumb' timer logic
        self.dumb_timer_cycle = ['north', 'east', 'south', 'west']
        self.dumb_timer_duration = 20 # seconds per green light
        self.dumb_timer_last_switch = 0
        self.dumb_timer_current_index = 0
        
        # Statistics
        self.total_cars_passed = 0
        self.total_wait_time = 0.0

    def _setup_intersection(self) -> Intersection:
        """Creates the lanes and the intersection for the simulation."""
        lanes = {
            'north': [Lane('North_1')],
            'south': [Lane('South_1')],
            'east': [Lane('East_1')],
            'west': [Lane('West_1')]
        }
        return Intersection(lanes)

    def _spawn_vehicles(self):
        """Randomly adds new vehicles to each direction's lanes."""
        for direction in self.intersection.signals:
            # We can have multiple lanes per direction, so we iterate
            for lane in self.intersection.get_lanes_for_direction(direction):
                if random.random() < VEHICLE_SPAWN_PROBABILITY:
                    # For demonstration, occasionally spawn an emergency vehicle
                    if random.random() < 0.02: # 2% chance of being an EV
                        ev_type = random.choice(['ambulance', 'fire_truck', 'police'])
                        lane.add_vehicle(Vehicle(vehicle_type=ev_type))
                    else:
                        lane.add_vehicle(Vehicle(vehicle_type='car'))
    
    def _update_dumb_timer(self, current_time):
        """Updates the traffic signals based on a fixed-cycle timer."""
        if current_time - self.dumb_timer_last_switch > self.dumb_timer_duration:
            self.dumb_timer_last_switch = current_time
            self.dumb_timer_current_index = (self.dumb_timer_current_index + 1) % len(self.dumb_timer_cycle)
            active_direction = self.dumb_timer_cycle[self.dumb_timer_current_index]
            self.intersection.set_signal_state(active_direction, 'green')

    def _update_ai_logic(self):
        """Updates traffic signals using the dynamic AI logic."""
        best_direction = self.ai_logic.decide_next_green(self.intersection)
        if best_direction:
            self.intersection.set_signal_state(best_direction, 'green')

    def _process_green_light(self):
        """Simulates vehicles passing through green lights."""
        active_signal = self.intersection.signals.get(self.intersection.active_direction)
        if not active_signal or active_signal.state != 'green':
            return

        for lane in active_signal.lanes:
            for _ in range(CARS_PER_SECOND_GREEN_LIGHT):
                vehicle = lane.remove_vehicle()
                if vehicle:
                    self.total_cars_passed += 1
                    wait_time = time.time() - vehicle.creation_time
                    self.total_wait_time += wait_time
                else:
                    break # No more vehicles in this lane

    def run(self):
        """Runs the main simulation loop."""
        print(f"\n--- Starting {self.logic_mode.upper()} Simulation ---")
        start_time = time.time()
        
        # Set an initial green light
        if self.logic_mode == 'dumb':
            initial_direction = self.dumb_timer_cycle[0]
            self.intersection.set_signal_state(initial_direction, 'green')
            self.dumb_timer_last_switch = time.time()
        else: # AI
            # For AI, let it decide the first green light based on initial spawns
            pass

        while True:
            current_time = time.time()
            elapsed_time = current_time - start_time
            if elapsed_time > SIMULATION_DURATION_SECONDS:
                break
            
            # --- Simulation Step ---
            self._spawn_vehicles()

            if self.logic_mode == 'ai':
                self._update_ai_logic()
            else: # 'dumb'
                self._update_dumb_timer(current_time)
            
            self._process_green_light()

            # --- Print Status (optional, for debugging) ---
            print(f"Time: {int(elapsed_time):03d}s | Active: {self.intersection.active_direction} | Cars Passed: {self.total_cars_passed}", end='\r')
            
            # Control simulation speed
            time.sleep(0.1) # Sleep for 100ms to make it about 10x faster than real-time

        # --- Print Final Results ---
        print("\n--- Simulation Ended ---")
        print(f"Total cars passed: {self.total_cars_passed}")
        avg_wait_time = self.total_wait_time / self.total_cars_passed if self.total_cars_passed > 0 else 0
        print(f"Average wait time per car: {avg_wait_time:.2f} seconds")
        return avg_wait_time, self.total_cars_passed


if __name__ == "__main__":
    # Run the 'dumb' simulation
    dumb_sim = Simulation(logic_mode='dumb')
    dumb_avg_wait, dumb_cars_passed = dumb_sim.run()

    # Run the 'ai' simulation
    ai_sim = Simulation(logic_mode='ai')
    ai_avg_wait, ai_cars_passed = ai_sim.run()
    
    # --- Final Comparison ---
    print("\n\n--- FINAL COMPARISON ---")
    print(f"{'Metric':<25} | {'Dumb Timer':<15} | {'AI Logic':<15}")
    print("-" * 60)
    print(f"{'Avg Wait Time (s)':<25} | {dumb_avg_wait:<15.2f} | {ai_avg_wait:<15.2f}")
    print(f"{'Total Cars Passed':<25} | {dumb_cars_passed:<15} | {ai_cars_passed:<15}")
    
    if dumb_avg_wait > 0:
        reduction = ((dumb_avg_wait - ai_avg_wait) / dumb_avg_wait) * 100
        print(f"\nImprovement in average wait time: {reduction:.2f}%")