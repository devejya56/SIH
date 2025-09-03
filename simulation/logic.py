from .engine import Intersection

class DynamicPriorityLogic:
    """
    The "brain" of the traffic system.
    
    This class contains the logic to analyze the state of an intersection
    and decide which direction should get the next green light.
    """
    def __init__(self, car_weight: float = 1.0, wait_time_weight: float = 0.5):
        """
        Initializes the AI logic with weights for its decision-making formula.
        
        Args:
            car_weight (float): The importance of the number of cars in a lane.
            wait_time_weight (float): The importance of how long a car has been waiting.
        """
        self.W1 = car_weight
        self.W2 = wait_time_weight
        # The print statement below is commented out to make the final output cleaner
        # print("AI Logic Initialized.")

    def decide_next_green(self, intersection: Intersection) -> str:
        """
        Decides the next direction to receive a green light based on a priority score.
        
        The logic first checks for any emergency vehicles. If found, it gives them
        absolute priority. Otherwise, it calculates a score for each direction
        and chooses the one with the highest score.
        
        Args:
            intersection (Intersection): The current state of the intersection.
            
        Returns:
            str: The direction that should get the next green light.
        """
        # 1. --- Emergency Vehicle Override ---
        # This is the highest priority check.
        for direction, signal in intersection.signals.items():
            for lane in signal.lanes:
                # Check only the first vehicle in the queue
                if lane.vehicles and lane.vehicles[0].is_emergency:
                    # print(f"EMERGENCY OVERRIDE: Emergency vehicle detected in '{lane.id}'.")
                    return direction

        # 2. --- Dynamic Priority Score Calculation ---
        # If no emergency, calculate scores for each direction.
        scores = {}
        for direction, signal in intersection.signals.items():
            # Don't switch away from a green light if its minimum time hasn't passed
            if intersection.active_direction == direction and not signal.is_min_time_passed():
                # print(f"AI Decision: Sticking with '{direction}' (min green time).")
                return direction

            direction_score = 0
            for lane in signal.lanes:
                # The score is a weighted sum of car count and longest wait time.
                car_count_score = lane.vehicle_count * self.W1
                wait_time_score = lane.get_longest_wait_time() * self.W2
                direction_score += car_count_score + wait_time_score
            scores[direction] = round(direction_score, 2)

        # 3. --- Decision ---
        # Find the direction with the highest score.
        if not scores:
            # Default to the first signal if something goes wrong
            return list(intersection.signals.keys())[0]
            
        best_direction = max(scores, key=scores.get)
        # The print statement below is commented out to make the final output cleaner
        # print(f"AI Decision: Scores={scores}, Best Direction='{best_direction}'")
        return best_direction