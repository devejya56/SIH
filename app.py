import streamlit as st
import time
import random
import numpy as np
import collections
import pandas as pd

# --- CORE SIMULATION LOGIC (HEAVILY REFACTORED) ---

# --- Models (Updated) ---
class Vehicle:
    _id_counter = 0
    def __init__(self, vehicle_type: str = 'car', creation_time: int = 0, turn_direction: str = 'straight'):
        Vehicle._id_counter += 1
        self.id = Vehicle._id_counter
        self.vehicle_type = vehicle_type
        self.creation_time = creation_time
        self.turn_direction = turn_direction

    @property
    def is_emergency(self) -> bool:
        return self.vehicle_type in ['ambulance', 'fire_truck', 'police']

class Lane:
    def __init__(self, lane_id: str):
        self.id = lane_id
        self.vehicles = collections.deque()

    def add_vehicle(self, vehicle: Vehicle): self.vehicles.append(vehicle)
    def remove_vehicle(self) -> Vehicle | None: return self.vehicles.popleft() if self.vehicles else None
    @property
    def vehicle_count(self) -> int: return len(self.vehicles)
    def get_longest_wait_time(self, current_time: int) -> float:
        if not self.vehicles: return 0.0
        return float(current_time - self.vehicles[0].creation_time)

# --- Engine (Updated) ---
class TrafficSignal:
    def __init__(self, lanes, min_green_duration: int = 10, yellow_duration: int = 3):
        self.lanes = lanes
        self.state = 'red' # Can be 'red', 'yellow', 'green'
        self.min_green_duration = min_green_duration
        self.yellow_duration = yellow_duration
        self.state_start_time = 0

    def set_state(self, state, current_time):
        self.state = state
        self.state_start_time = current_time

    def is_min_time_passed(self, current_time: int) -> bool:
        if self.state == 'green':
            return (current_time - self.state_start_time) >= self.min_green_duration
        return True

    def is_yellow_time_passed(self, current_time: int) -> bool:
        if self.state == 'yellow':
            return (current_time - self.state_start_time) >= self.yellow_duration
        return True

class Intersection:
    # Defines which lanes can be green at the same time (Phases)
    PHASES = {
        'NS_Straight': ['north_straight', 'south_straight'],
        'EW_Straight': ['east_straight', 'west_straight'],
        'N_Left': ['north_left'],
        'S_Left': ['south_left'],
        'E_Left': ['east_left'],
        'W_Left': ['west_left'],
    }

    def __init__(self, configuration):
        self.lanes = {lane_id: Lane(lane_id) for lane_id in configuration}
        self.signals = {phase: TrafficSignal(lanes=[self.lanes[lane_id] for lane_id in lane_ids]) for phase, lane_ids in self.PHASES.items()}
        self.active_phase = None
        self.is_in_yellow_phase = False

    def get_lane(self, lane_id): return self.lanes.get(lane_id)

    def set_phase(self, phase_name: str, current_time: int):
        if self.active_phase == phase_name:
            return

        # If a phase is currently active, switch it to yellow first
        if self.active_phase and not self.is_in_yellow_phase:
            active_signal = self.signals[self.active_phase]
            if not active_signal.is_min_time_passed(current_time):
                return # Don't switch if min green time not met
            active_signal.set_state('yellow', current_time)
            self.is_in_yellow_phase = True
            self.next_phase = phase_name # Remember which phase to switch to after yellow
            return

        # Turn all signals red
        for signal in self.signals.values():
            signal.set_state('red', current_time)

        # Activate the new phase
        if phase_name in self.signals:
            self.signals[phase_name].set_state('green', current_time)
            self.active_phase = phase_name
            self.is_in_yellow_phase = False
            self.next_phase = None

    def update_yellow_phase(self, current_time):
        if not self.is_in_yellow_phase or not self.active_phase:
            return
        
        if self.signals[self.active_phase].is_yellow_time_passed(current_time):
            self.set_phase(self.next_phase, current_time)

# --- Logic (Updated) ---
class DynamicPriorityLogic:
    def __init__(self, car_weight: float = 1.0, wait_time_weight: float = 0.5):
        self.W1 = car_weight
        self.W2 = wait_time_weight
        self.MAX_WAIT_THRESHOLD = 120 # Starvation prevention

    def decide_next_phase(self, intersection: Intersection, current_time: int) -> str:
        # 1. Starvation Prevention
        starving_lane = None
        for lane in intersection.lanes.values():
            if lane.get_longest_wait_time(current_time) > self.MAX_WAIT_THRESHOLD:
                starving_lane = lane.id
                break
        if starving_lane:
            for phase, lane_ids in intersection.PHASES.items():
                if starving_lane in lane_ids:
                    return phase

        # 2. Emergency Vehicle Override
        for phase, lane_ids in intersection.PHASES.items():
            for lane_id in lane_ids:
                lane = intersection.get_lane(lane_id)
                if lane.vehicles and lane.vehicles[0].is_emergency:
                    return phase
        
        # 3. Dynamic Priority Score Calculation per Phase
        scores = {}
        for phase, lane_ids in intersection.PHASES.items():
            if intersection.active_phase == phase and not intersection.signals[phase].is_min_time_passed(current_time):
                return phase
            
            phase_score = 0
            for lane_id in lane_ids:
                lane = intersection.get_lane(lane_id)
                phase_score += lane.vehicle_count * self.W1
                phase_score += lane.get_longest_wait_time(current_time) * self.W2
            scores[phase] = round(phase_score, 2)
            
        if not scores: return list(intersection.PHASES.keys())[0]
        return max(scores, key=scores.get)

# --- STREAMLIT SIMULATION ORCHESTRATOR (Updated) ---
class StreamlitSimulation:
    def __init__(self, logic_mode: str, profile: dict, dumb_duration: int, car_weight: float = 1.0, wait_time_weight: float = 0.5):
        self.logic_mode = logic_mode
        self.profile = profile
        self.intersection = self._setup_intersection()
        self.ai_logic = DynamicPriorityLogic(car_weight, wait_time_weight)
        self.current_time = 0
        self.dumb_timer_cycle = list(Intersection.PHASES.keys())
        self.dumb_timer_duration = dumb_duration
        self.dumb_timer_last_switch = 0
        self.dumb_timer_current_index = 0
        self.total_cars_passed = 0
        self.total_wait_time = 0.0
        self.event_log = []

    def _setup_intersection(self):
        lane_ids = [
            'north_straight', 'north_left', 'south_straight', 'south_left',
            'east_straight', 'east_left', 'west_straight', 'west_left'
        ]
        return Intersection(lane_ids)

    def inject_emergency_vehicle(self, lane_id: str, ev_type: str):
        lane = self.intersection.get_lane(lane_id)
        if lane:
            lane.vehicles.appendleft(Vehicle(vehicle_type=ev_type, creation_time=self.current_time))

    def step(self):
        # 1. Update yellow phase first
        self.intersection.update_yellow_phase(self.current_time)
        if self.intersection.is_in_yellow_phase:
            self.current_time += 1
            return

        # 2. Spawn new vehicles based on profile
        for lane_id, spawn_prob in self.profile.items():
            if random.random() < spawn_prob:
                turn = 'left' if 'left' in lane_id else 'straight'
                self.intersection.get_lane(lane_id).add_vehicle(Vehicle(creation_time=self.current_time, turn_direction=turn))

        # 3. Update signal logic
        if self.logic_mode == 'ai':
            best_phase = self.ai_logic.decide_next_phase(self.intersection, self.current_time)
            if best_phase: self.intersection.set_phase(best_phase, self.current_time)
        else: # Dumb timer
            if self.current_time - self.dumb_timer_last_switch >= self.dumb_timer_duration:
                self.dumb_timer_last_switch = self.current_time
                self.dumb_timer_current_index = (self.dumb_timer_current_index + 1) % len(self.dumb_timer_cycle)
                active_phase = self.dumb_timer_cycle[self.dumb_timer_current_index]
                self.intersection.set_phase(active_phase, self.current_time)
        
        # 4. Process green lights
        if self.intersection.active_phase:
            active_signal = self.intersection.signals[self.intersection.active_phase]
            if active_signal.state == 'green':
                for lane in active_signal.lanes:
                    vehicle = lane.remove_vehicle()
                    if vehicle:
                        self.total_cars_passed += 1
                        wait_time = self.current_time - vehicle.creation_time
                        self.total_wait_time += wait_time
                        self.event_log.append({
                            'time_step': self.current_time, 'vehicle_id': vehicle.id,
                            'origin_lane': lane.id, 'wait_time': wait_time
                        })
        self.current_time += 1

    @property
    def average_wait_time(self):
        return self.total_wait_time / self.total_cars_passed if self.total_cars_passed > 0 else 0


# --- STREAMLIT APP UI ---

st.set_page_config(page_title="Project Sentinel", layout="wide")

st.title("🚦 Project Sentinel: Intelligent Traffic Management")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🕹️ System Controls")
start_button = st.sidebar.button("⏯️ Start / Stop Simulation")
reset_button = st.sidebar.button("🔄 Reset Simulation")

st.sidebar.header("🛠️ Simulation Parameters")
TRAFFIC_PROFILES = {
    "Balanced Flow": {
        'north_straight': 0.1, 'north_left': 0.05, 'south_straight': 0.1, 'south_left': 0.05,
        'east_straight': 0.1, 'east_left': 0.05, 'west_straight': 0.1, 'west_left': 0.05,
    },
    "Main Road Rush Hour": {
        'north_straight': 0.3, 'north_left': 0.15, 'south_straight': 0.3, 'south_left': 0.15,
        'east_straight': 0.05, 'east_left': 0.02, 'west_straight': 0.05, 'west_left': 0.02,
    },
    "Side Road Spillover": {
        'north_straight': 0.1, 'north_left': 0.05, 'south_straight': 0.1, 'south_left': 0.05,
        'east_straight': 0.25, 'east_left': 0.1, 'west_straight': 0.25, 'west_left': 0.1,
    }
}
profile_choice = st.sidebar.selectbox("Select Traffic Profile", list(TRAFFIC_PROFILES.keys()))
dumb_duration = st.sidebar.slider("Fixed-Timer Green Duration (s)", 10, 60, 20, 5)

st.sidebar.header("🧠 Tune the AI's Brain")
w1 = st.sidebar.slider("Car Count Weight (W1)", 0.1, 2.0, 1.0, 0.1)
w2 = st.sidebar.slider("Wait Time Weight (W2)", 0.1, 2.0, 0.5, 0.1)

# --- SESSION STATE INITIALIZATION ---
if 'running' not in st.session_state:
    st.session_state.running = False
if 'sims' not in st.session_state or reset_button:
    st.session_state.running = False
    st.session_state.sims = {
        'dumb': StreamlitSimulation('dumb', TRAFFIC_PROFILES[profile_choice], dumb_duration),
        'ai': StreamlitSimulation('ai', TRAFFIC_PROFILES[profile_choice], dumb_duration, w1, w2)
    }
    st.session_state.final_results = None

if start_button:
    st.session_state.running = not st.session_state.running
    if not st.session_state.running:
        st.session_state.final_results = {
            "dumb": (st.session_state.sims['dumb'].average_wait_time, st.session_state.sims['dumb'].total_cars_passed, st.session_state.sims['dumb'].event_log),
            "ai": (st.session_state.sims['ai'].average_wait_time, st.session_state.sims['ai'].total_cars_passed, st.session_state.sims['ai'].event_log)
        }

# --- MAIN PAGE LAYOUT WITH TABS ---
tab1, tab2 = st.tabs(["🚀 Live Simulation", "📊 Post-Run Analysis"])

# --- HTML/CSS for Traffic Light ---
LIGHT_CSS = """
<style>
    .light-box { background-color: #262730; border-radius: 10px; padding: 10px; display: inline-block; }
    .light-circle { width: 20px; height: 20px; border-radius: 50%; background-color: #4A5568; margin: 4px 0; }
    .light-red { background-color: #E53E3E; box-shadow: 0 0 10px #E53E3E;}
    .light-yellow { background-color: #ECC94B; box-shadow: 0 0 10px #ECC94B;}
    .light-green { background-color: #48BB78; box-shadow: 0 0 10px #48BB78;}
</style>
"""
st.markdown(LIGHT_CSS, unsafe_allow_html=True)

def create_traffic_light_html(state):
    red_class = "light-red" if state == 'red' else ""
    yellow_class = "light-yellow" if state == 'yellow' else ""
    green_class = "light-green" if state == 'green' else ""
    return f"""
    <div class="light-box">
        <div class="light-circle {red_class}"></div>
        <div class="light-circle {yellow_class}"></div>
        <div class="light-circle {green_class}"></div>
    </div>"""

with tab1:
    col1, col2 = st.columns(2)

    def render_simulation_state(sim_type, column):
        sim = st.session_state.sims[sim_type]
        title = "Standard 'Dumb' Timer" if sim_type == 'dumb' else "Project Sentinel 'Dynamic AI'"
        with column:
            st.subheader(title, divider='red' if sim_type == 'dumb' else 'blue')
            st.metric("Time (s)", sim.current_time)
            st.markdown("---")
            
            directions = {'North': ['north_straight', 'north_left'], 'South': ['south_straight', 'south_left'],
                          'East': ['east_straight', 'east_left'], 'West': ['west_straight', 'west_left']}
            
            for dir_name, lane_ids in directions.items():
                st.markdown(f"**{dir_name} Direction**")
                lane_cols = st.columns(2)
                for i, lane_id in enumerate(lane_ids):
                    lane = sim.intersection.get_lane(lane_id)
                    # Determine signal state for this specific lane
                    signal_state = 'red'
                    for phase, phases_lanes in sim.intersection.PHASES.items():
                        if lane_id in phases_lanes:
                            signal_state = sim.intersection.signals[phase].state
                            break
                    
                    with lane_cols[i]:
                        light_html = create_traffic_light_html(signal_state)
                        st.markdown(f"*{'Left' if 'left' in lane_id else 'Straight'}*", unsafe_allow_html=True)
                        st.markdown(light_html, unsafe_allow_html=True)
                        cars = "".join(["🚑" if v.is_emergency else "🚗" for v in lane.vehicles])
                        st.markdown(f"`[{lane.vehicle_count}]` {cars}")

            if sim_type == 'ai':
                st.markdown("---")
                st.markdown("**Inject Emergency Vehicle:**")
                ev_cols = st.columns(4)
                if ev_cols[0].button("🚑 N Straight"): sim.inject_emergency_vehicle('north_straight', 'ambulance')
                if ev_cols[1].button("🚒 E Left"): sim.inject_emergency_vehicle('east_left', 'fire_truck')
                if ev_cols[2].button("🚓 S Straight"): sim.inject_emergency_vehicle('south_straight', 'police')
                if ev_cols[3].button("🚑 W Left"): sim.inject_emergency_vehicle('west_left', 'ambulance')

    render_simulation_state('dumb', col1)
    render_simulation_state('ai', col2)

with tab2:
    st.header("🔬 Final Results Summary")
    if st.session_state.final_results:
        dumb_wait, dumb_passed, dumb_log = st.session_state.final_results['dumb']
        ai_wait, ai_passed, ai_log = st.session_state.final_results['ai']

        st.success(f"🏆 The AI Logic reduced the average wait time by **{((dumb_wait - ai_wait) / dumb_wait) * 100:.2f}%**.")

        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.subheader("Key Performance Indicators")
            chart_data = pd.DataFrame({
                "System": ["Dumb Timer", "AI Logic"],
                "Average Wait Time (s)": [dumb_wait, ai_wait],
                "Total Cars Passed": [dumb_passed, ai_passed]
            })
            st.dataframe(chart_data.set_index('System'))

        with res_col2:
            st.subheader("Performance Comparison Chart")
            st.bar_chart(chart_data, x="System", y="Average Wait Time (s)")
        
        st.subheader("📄 Simulation Event Log")
        log_df = pd.DataFrame(ai_log)
        st.dataframe(log_df)
        csv = log_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name='ai_simulation_log.csv',
            mime='text/csv',
        )
    else:
        st.info("Run a simulation and then click 'Stop' to see the final analysis here.")

# --- MAIN APP LOOP ---
if st.session_state.running:
    st.session_state.sims['ai'].ai_logic.W1 = w1
    st.session_state.sims['ai'].ai_logic.W2 = w2
    
    st.session_state.sims['dumb'].step()
    st.session_state.sims['ai'].step()

    time.sleep(0.5)
    st.rerun()
