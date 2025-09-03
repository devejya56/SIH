import streamlit as st
import time
import random
import numpy as np
import collections
import pandas as pd

# --- CORE SIMULATION LOGIC (Consolidated into one file) ---
# This section contains all the backend classes for the simulation engine.

# --- Models ---
class Vehicle:
    _id_counter = 0
    def __init__(self, vehicle_type: str = 'car', creation_time: int = 0):
        Vehicle._id_counter += 1
        self.id = Vehicle._id_counter
        self.vehicle_type = vehicle_type
        self.creation_time = creation_time

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

# --- Engine ---
class TrafficSignal:
    def __init__(self, lanes, min_green_duration: int = 15):
        self.lanes = lanes
        self.state = 'red'
        self.min_green_duration = min_green_duration
        self.green_start_time = 0

    def turn_green(self, current_time: int):
        self.state = 'green'
        self.green_start_time = current_time

    def turn_red(self):
        self.state = 'red'
        self.green_start_time = 0

    def is_min_time_passed(self, current_time: int) -> bool:
        if self.state == 'green':
            return (current_time - self.green_start_time) >= self.min_green_duration
        return True

class Intersection:
    def __init__(self, configuration):
        self.signals = {direction: TrafficSignal(lanes) for direction, lanes in configuration.items()}
        self.active_direction = None

    def get_lanes_for_direction(self, direction: str): return self.signals[direction].lanes
    def set_signal_state(self, direction: str, state: str, current_time: int):
        if state != 'green': raise ValueError("Can only set a signal to 'green'")
        if self.active_direction == direction and not self.signals[direction].is_min_time_passed(current_time):
            return
        for d, signal in self.signals.items():
            if d != direction: signal.turn_red()
        self.signals[direction].turn_green(current_time)
        self.active_direction = direction

# --- Logic ---
class DynamicPriorityLogic:
    def __init__(self, car_weight: float = 1.0, wait_time_weight: float = 0.5):
        self.W1 = car_weight
        self.W2 = wait_time_weight

    def decide_next_green(self, intersection: Intersection, current_time: int) -> str:
        for direction, signal in intersection.signals.items():
            for lane in signal.lanes:
                if lane.vehicles and lane.vehicles[0].is_emergency:
                    return direction
        scores = {}
        for direction, signal in intersection.signals.items():
            if intersection.active_direction == direction and not signal.is_min_time_passed(current_time):
                return direction
            direction_score = 0
            for lane in signal.lanes:
                direction_score += lane.vehicle_count * self.W1
                direction_score += lane.get_longest_wait_time(current_time) * self.W2
            scores[direction] = round(direction_score, 2)
        if not scores: return list(intersection.signals.keys())[0]
        return max(scores, key=scores.get)

# --- STREAMLIT SIMULATION ORCHESTRATOR ---
class StreamlitSimulation:
    def __init__(self, logic_mode: str, spawn_prob: float, dumb_duration: int, car_weight: float = 1.0, wait_time_weight: float = 0.5):
        self.logic_mode = logic_mode
        self.spawn_prob = spawn_prob
        self.intersection = self._setup_intersection()
        self.ai_logic = DynamicPriorityLogic(car_weight, wait_time_weight)
        self.current_time = 0
        self.dumb_timer_cycle = ['north', 'east', 'south', 'west']
        self.dumb_timer_duration = dumb_duration
        self.dumb_timer_last_switch = 0
        self.dumb_timer_current_index = 0
        self.total_cars_passed = 0
        self.total_wait_time = 0.0
        self.wait_times_data = []

        if self.logic_mode == 'dumb':
            self.intersection.set_signal_state(self.dumb_timer_cycle[0], 'green', self.current_time)

    def _setup_intersection(self):
        lanes = {'north': [Lane('N')], 'south': [Lane('S')], 'east': [Lane('E')], 'west': [Lane('W')]}
        return Intersection(lanes)

    def inject_emergency_vehicle(self, direction: str, ev_type: str):
        if direction in self.intersection.signals:
            lane = self.intersection.get_lanes_for_direction(direction)[0]
            lane.vehicles.appendleft(Vehicle(vehicle_type=ev_type, creation_time=self.current_time))

    def step(self):
        # 1. Spawn vehicles
        for direction in self.intersection.signals:
            if random.random() < self.spawn_prob:
                self.intersection.get_lanes_for_direction(direction)[0].add_vehicle(Vehicle(creation_time=self.current_time))
        # 2. Update signal logic
        if self.logic_mode == 'ai':
            best_direction = self.ai_logic.decide_next_green(self.intersection, self.current_time)
            if best_direction: self.intersection.set_signal_state(best_direction, 'green', self.current_time)
        else: # Dumb timer
            if self.current_time - self.dumb_timer_last_switch >= self.dumb_timer_duration:
                self.dumb_timer_last_switch = self.current_time
                self.dumb_timer_current_index = (self.dumb_timer_current_index + 1) % len(self.dumb_timer_cycle)
                active_direction = self.dumb_timer_cycle[self.dumb_timer_current_index]
                self.intersection.set_signal_state(active_direction, 'green', self.current_time)
        # 3. Process green light
        active_dir = self.intersection.active_direction
        if active_dir and self.intersection.signals[active_dir].state == 'green':
            vehicle = self.intersection.get_lanes_for_direction(active_dir)[0].remove_vehicle()
            if vehicle:
                self.total_cars_passed += 1
                wait_time = self.current_time - vehicle.creation_time
                self.total_wait_time += wait_time
                self.wait_times_data.append(wait_time)
        self.current_time += 1

    @property
    def average_wait_time(self):
        return self.total_wait_time / self.total_cars_passed if self.total_cars_passed > 0 else 0


# --- STREAMLIT APP UI ---

st.set_page_config(page_title="Intelligent Traffic Control Systems", layout="wide")

st.title("🚦 Intelligent Traffic Control Systems")
st.markdown("An advanced dashboard for simulating and analyzing an AI-powered traffic control system.")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🕹️ System Controls")
start_button = st.sidebar.button("⏯️ Start / Stop Simulation")
reset_button = st.sidebar.button("🔄 Reset Simulation")

st.sidebar.header("🛠️ Simulation Parameters")
spawn_prob = st.sidebar.slider("Vehicle Spawn Probability", 0.1, 1.0, 0.35, 0.05, help="How likely a new car is to appear in a lane each second.")
dumb_duration = st.sidebar.slider("Fixed-Timer Green Duration (s)", 10, 60, 30, 5, help="How long each light stays green in the 'Dumb' system.")

st.sidebar.header("🧠 Tune the AI's Brain")
w1 = st.sidebar.slider("Car Count Weight (W1)", 0.1, 2.0, 1.0, 0.1, help="Higher values prioritize clearing heavy congestion.")
w2 = st.sidebar.slider("Wait Time Weight (W2)", 0.1, 2.0, 0.5, 0.1, help="Higher values prioritize fairness for cars waiting a long time.")

st.sidebar.header("🚨 Inject Emergency Vehicle")
st.sidebar.markdown("*(Only affects the AI simulation)*")
ev_col1, ev_col2 = st.sidebar.columns(2)
if ev_col1.button("🚑 Ambulance (N)"):
    if 'sims' in st.session_state: st.session_state.sims['ai'].inject_emergency_vehicle('north', 'ambulance')
if ev_col1.button("🚓 Police Car (S)"):
    if 'sims' in st.session_state: st.session_state.sims['ai'].inject_emergency_vehicle('south', 'police')
if ev_col2.button("🚒 Fire Truck (E)"):
    if 'sims' in st.session_state: st.session_state.sims['ai'].inject_emergency_vehicle('east', 'fire_truck')
if ev_col2.button("🚑 Ambulance (W)"):
    if 'sims' in st.session_state: st.session_state.sims['ai'].inject_emergency_vehicle('west', 'ambulance')

# --- SESSION STATE INITIALIZATION ---
if 'running' not in st.session_state:
    st.session_state.running = False
if 'sims' not in st.session_state or reset_button:
    st.session_state.running = False
    st.session_state.sims = {
        'dumb': StreamlitSimulation('dumb', spawn_prob, dumb_duration),
        'ai': StreamlitSimulation('ai', spawn_prob, dumb_duration, w1, w2)
    }
    st.session_state.final_results = None

if start_button:
    st.session_state.running = not st.session_state.running
    if not st.session_state.running: # If we just stopped it
        st.session_state.final_results = {
            "dumb": (st.session_state.sims['dumb'].average_wait_time, st.session_state.sims['dumb'].total_cars_passed),
            "ai": (st.session_state.sims['ai'].average_wait_time, st.session_state.sims['ai'].total_cars_passed)
        }

# --- MAIN PAGE LAYOUT WITH TABS ---
tab1, tab2 = st.tabs(["🚀 Live Simulation", "📊 Post-Run Analysis"])

# --- HTML/CSS for Traffic Light ---
LIGHT_CSS = """
<style>
    .light-box {
        background-color: #262730;
        border-radius: 10px;
        padding: 10px;
        display: inline-block;
        margin-right: 20px;
    }
    .light-circle {
        width: 25px;
        height: 25px;
        border-radius: 50%;
        background-color: #4A5568; /* Dim default */
        margin: 5px 0;
    }
    .light-red { background-color: #E53E3E; box-shadow: 0 0 15px #E53E3E;}
    .light-green { background-color: #48BB78; box-shadow: 0 0 15px #48BB78;}
</style>
"""
st.markdown(LIGHT_CSS, unsafe_allow_html=True)

def create_traffic_light_html(state):
    red_class = "light-red" if state == 'red' else ""
    green_class = "light-green" if state == 'green' else ""
    return f"""
    <div class="light-box">
        <div class="light-circle {red_class}"></div>
        <div class="light-circle {green_class}"></div>
    </div>
    """

with tab1:
    st.header("🔴 Live Dashboard")
    col1, col2 = st.columns(2)

    def render_simulation_state(sim_type, column):
        sim = st.session_state.sims[sim_type]
        title = "Standard 'Dumb' Timer" if sim_type == 'dumb' else "Intelligent 'Dynamic AI' System"
        with column:
            st.subheader(title, divider='red' if sim_type == 'dumb' else 'blue')
            st.markdown("<h6>⏱️ STATUS</h6>", unsafe_allow_html=True)
            status_cols = st.columns([1, 2])
            with status_cols[0]:
                 active_dir = sim.intersection.active_direction
                 light_state = sim.intersection.signals[active_dir].state if active_dir else 'red'
                 st.markdown(create_traffic_light_html(light_state), unsafe_allow_html=True)
            with status_cols[1]:
                st.write(f"**Active Direction:**")
                st.write(f"### {active_dir.capitalize() if active_dir else 'None'}")
            
            if sim.logic_mode == 'dumb' and sim.intersection.active_direction:
                progress = (sim.current_time - sim.dumb_timer_last_switch) / sim.dumb_timer_duration
                st.progress(min(progress, 1.0), text="Time Until Next Switch")
            elif sim.logic_mode == 'ai' and sim.intersection.active_direction:
                signal = sim.intersection.signals[sim.intersection.active_direction]
                progress = (sim.current_time - signal.green_start_time) / signal.min_green_duration
                st.progress(min(progress, 1.0), text="Minimum Green Time")
            
            st.markdown("<h6>📊 METRICS</h6>", unsafe_allow_html=True)
            kpi_cols = st.columns(3)
            kpi_cols[0].metric("Avg Wait (s)", f"{sim.average_wait_time:.2f}")
            kpi_cols[1].metric("Cars Passed", sim.total_cars_passed)
            kpi_cols[2].metric("Time (s)", sim.current_time)

            st.markdown("<h6>🚗 LIVE LANES</h6>", unsafe_allow_html=True)
            for direction, signal in sorted(sim.intersection.signals.items()):
                cars = ""
                for v in signal.lanes[0].vehicles:
                    if v.vehicle_type == 'ambulance': cars += "🚑"
                    elif v.vehicle_type == 'fire_truck': cars += "🚒"
                    elif v.vehicle_type == 'police': cars += "🚓"
                    else: cars += "🚗"
                st.markdown(f"**{direction.capitalize()}:** `[{signal.lanes[0].vehicle_count}]` {cars}")
            
    render_simulation_state('dumb', col1)
    render_simulation_state('ai', col2)
    
with tab2:
    st.header("🔬 Final Results Summary")
    if st.session_state.final_results:
        dumb_wait, dumb_passed = st.session_state.final_results['dumb']
        ai_wait, ai_passed = st.session_state.final_results['ai']

        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.subheader("Key Performance Indicators")
            st.metric("Avg Wait Time (Dumb Timer)", f"{dumb_wait:.2f} s")
            st.metric("Avg Wait Time (AI Logic)", f"{ai_wait:.2f} s", delta=f"{ai_wait - dumb_wait:.2f} s")
            st.divider()
            st.metric("Total Cars Passed (Dumb Timer)", f"{dumb_passed}")
            st.metric("Total Cars Passed (AI Logic)", f"{ai_passed}", delta=f"{ai_passed - dumb_passed}")

        with res_col2:
            st.subheader("Performance Comparison")
            if dumb_wait > 0:
                wait_reduction = ((dumb_wait - ai_wait) / dumb_wait) * 100
                st.success(f"🏆 The AI Logic reduced the average wait time by **{wait_reduction:.2f}%**.")
            
            chart_data = pd.DataFrame({
                "System": ["Dumb Timer", "AI Logic"],
                "Average Wait Time (s)": [dumb_wait, ai_wait],
                "Total Cars Passed": [dumb_passed, ai_passed]
            })
            st.bar_chart(chart_data, x="System", y="Average Wait Time (s)")
            st.bar_chart(chart_data, x="System", y="Total Cars Passed")

    else:
        st.info("Run a simulation and then click 'Stop' to see the final analysis here.")

# --- MAIN APP LOOP ---
if st.session_state.running:
    # Update AI logic with slider values
    st.session_state.sims['ai'].ai_logic.W1 = w1
    st.session_state.sims['ai'].ai_logic.W2 = w2
    
    # Update simulation parameters
    st.session_state.sims['dumb'].dumb_timer_duration = dumb_duration
    st.session_state.sims['dumb'].spawn_prob = spawn_prob
    st.session_state.sims['ai'].spawn_prob = spawn_prob

    st.session_state.sims['dumb'].step()
    st.session_state.sims['ai'].step()

    time.sleep(0.5)
    st.rerun()

