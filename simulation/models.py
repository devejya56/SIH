# simulation/models.py

import time
import collections
import itertools

class Vehicle:
    """
    Represents a single vehicle in the simulation.
    
    Each vehicle has a unique ID, a type (which determines if it's an emergency vehicle),
    and a creation time to track how long it has been waiting.
    """
    # A class-level counter to ensure unique IDs for each vehicle
    id_counter = itertools.count(start=1)

    def __init__(self, vehicle_type: str = 'car'):
        """
        Initializes a Vehicle.
        
        Args:
            vehicle_type (str): The type of vehicle. Can be 'car', 'ambulance',
                                'fire_truck', or 'police'.
        """
        self.id = next(Vehicle.id_counter)
        self.vehicle_type = vehicle_type
        self.creation_time = time.time()

    @property
    def is_emergency(self) -> bool:
        """Returns True if the vehicle is an emergency vehicle."""
        return self.vehicle_type in ['ambulance', 'fire_truck', 'police']

    def __repr__(self) -> str:
        """String representation of the Vehicle."""
        emergency_status = " (E)" if self.is_emergency else ""
        return f"Vehicle(id={self.id}, type={self.vehicle_type}{emergency_status})"


class Lane:
    """
    Represents a single lane of traffic approaching an intersection.
    
    A lane is essentially a queue of vehicles. It provides methods to manage
    the vehicles and calculate key metrics for our AI logic.
    """
    def __init__(self, lane_id: str):
        """
        Initializes a Lane.
        
        Args:
            lane_id (str): A unique identifier for the lane (e.g., "Northbound_1").
        """
        self.id = lane_id
        # We use a deque as it's highly efficient for adding (append) and
        # removing (popleft) items from the ends, simulating a vehicle queue.
        self.vehicles = collections.deque()

    def add_vehicle(self, vehicle: Vehicle):
        """Adds a vehicle to the end of the lane's queue."""
        self.vehicles.append(vehicle)

    def remove_vehicle(self) -> Vehicle | None:
        """Removes and returns the vehicle at the front of the queue."""
        if self.vehicles:
            return self.vehicles.popleft()
        return None

    @property
    def vehicle_count(self) -> int:
        """Returns the number of vehicles currently in the lane."""
        return len(self.vehicles)

    def get_longest_wait_time(self) -> float:
        """
        Calculates the waiting time of the vehicle at the front of the queue.
        
        Returns:
            float: The wait time in seconds, or 0 if the lane is empty.
        """
        if not self.vehicles:
            return 0.0
        
        # The vehicle at the front of the queue (index 0) has been waiting the longest.
        oldest_vehicle = self.vehicles[0]
        wait_time = time.time() - oldest_vehicle.creation_time
        return wait_time

    def __repr__(self) -> str:
        """String representation of the Lane."""
        return f"Lane(id={self.id}, vehicles={self.vehicle_count})"

# --- Example Usage & Unit Test ---
# This block allows us to test the models directly by running: python simulation/models.py
if __name__ == '__main__':
    print("--- Testing Vehicle Class ---")
    car = Vehicle(vehicle_type='car')
    ambulance = Vehicle(vehicle_type='ambulance')
    print(car)
    print(f"Is car an emergency vehicle? {car.is_emergency}")
    print(ambulance)
    print(f"Is ambulance an emergency vehicle? {ambulance.is_emergency}")

    print("\n--- Testing Lane Class ---")
    northbound_lane = Lane(lane_id="Northbound_1")
    print(northbound_lane)
    
    northbound_lane.add_vehicle(car)
    northbound_lane.add_vehicle(Vehicle(vehicle_type='car'))
    print(f"After adding two cars: {northbound_lane}")
    
    print(f"Longest wait time before delay: {northbound_lane.get_longest_wait_time():.2f}s")
    
    # Simulate a 2-second delay
    time.sleep(2)
    
    northbound_lane.add_vehicle(ambulance)
    print(f"After adding an ambulance 2s later: {northbound_lane}")
    print(f"Longest wait time after delay: {northbound_lane.get_longest_wait_time():.2f}s")
    
    front_vehicle = northbound_lane.remove_vehicle()
    print(f"Removed front vehicle: {front_vehicle}")
    print(f"Lane state after removal: {northbound_lane}")