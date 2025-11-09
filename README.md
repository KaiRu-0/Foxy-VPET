# Foxy VPET 🦊

> An interactive desktop pet that learns from your interactions using reinforcement learning

---

## 📖 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
  - [Animation States](#animation-states)
  - [Reinforcement Learning](#reinforcement-learning)
  - [State Machine](#state-machine)
- [Architecture](#architecture)
- [Learning Algorithm](#learning-algorithm)
- [Customization](#customization)
- [File Structure](#file-structure)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

Foxy is an interactive desktop pet that lives on your screen and learns from your behavior. Using a simple yet effective reinforcement learning algorithm, Foxy adapts its actions based on which behaviors you respond to positively (by clicking). Over time, Foxy will do more of what you like and less of what you ignore!

**Key Concept**: Click on Foxy when it does something you like, and it will learn to do that more often.

---

## ✨ Features

- 🎨 **5 Animated States**: idle, excited, relax, sleep, and walk
- 🧠 **Reinforcement Learning**: Learns from user interactions
- 💾 **Persistent Memory**: Remembers preferences across sessions
- 🖱️ **Drag & Drop**: Moveable anywhere on screen
- 🪟 **Always on Top**: Stays visible above other windows
- 🎭 **Transparent Background**: Only the fox is visible
- ⚡ **Smooth Animations**: 24 FPS sprite animation

---

## 📦 Installation

### Prerequisites

- Python 3.7 or higher
- pip package manager

### Install Dependencies

```bash
pip install PyQt5
```

### Clone Repository

```bash
git clone https://github.com/yourusername/foxy-vpet.git
cd foxy-vpet
```

---

## 🚀 Quick Start

1. Ensure your animation files are in the correct structure (see [File Structure](#file-structure))

2. Run the application:
   ```bash
   python foxy_vpet.py
   ```

3. Interact with Foxy:
   - **Click** on Foxy when it does something you like
   - **Drag** Foxy to reposition it on your screen
   - Watch as Foxy learns your preferences over time!

4. The learning state is automatically saved to `foxy_brain.json`

---

## 🔍 How It Works

### Animation States

Foxy has **5 different behavioral states**:

| State | Description | Duration | Frames |
|-------|-------------|----------|--------|
| 🟢 **idle** | Default resting state | 2-10 seconds | 24 |
| 🎉 **excited** | Energetic, happy behavior | 3 seconds | 24 |
| 😌 **relax** | Calm, peaceful behavior | 3 seconds | 24 |
| 😴 **sleep** | Sleeping/drowsy behavior | 3 seconds | 24 |
| 🚶 **walk** | Walking/moving behavior | 3 seconds | 24 |

### Reinforcement Learning

Foxy uses a **weighted random selection** algorithm:

1. Each action (excited, relax, sleep, walk) has a **weight** (starts at 1.0)
2. Actions with higher weights are **more likely** to be selected
3. When you **click** during an action: weight increases (+0.15)
4. When you **ignore** an action: weight decreases (-0.05)
5. Over time, Foxy learns to do what you like!

#### Exploration vs Exploitation

```
30% 🔍 Exploration: Random action (discover new preferences)
70% 🎯 Exploitation: Weight-based selection (use learned preferences)
```

This ensures Foxy keeps trying new things while primarily doing what you've shown you enjoy.

### State Machine

```
┌────────────────────────────────────────────────┐
│                                                │
│  ┌──────┐                                      │
│  │ IDLE │ ◄─────────────────────────────┐      │
│  └──┬───┘                               │      │
│     │                                   │      │
│     │ (2-10 sec rest)                   │      │
│     │ Brain chooses action              │      │
│     │                                   │      │
│     ├────────┬────────┬────────┬────────┤      │
│     ▼        ▼        ▼        ▼        │      │
│  ┌──────┐┌──────┐┌──────┐┌──────┐       │      │
│  │EXCITE││RELAX ││SLEEP ││ WALK │       │      │
│  │  D   ││      ││      ││      │       │      │
│  └───┬──┘└───┬──┘└───┬──┘└───┬──┘       │      │
│      │       │       │       │          │      │
│      └───────┴───────┴───────┴──────────┘      │
│               (3 sec action)                   │
│         User clicks or ignores                 │
│                                                │
└────────────────────────────────────────────────┘
```

**Flow**:
1. Start in **idle** state (2-10 seconds)
2. Brain chooses an action based on learned weights
3. Perform action for **3 seconds** (72 frames at 24 FPS)
4. Record if user clicked (positive feedback) or ignored (negative feedback)
5. Update weights and return to **idle**

---

## 🏗️ Architecture

The application consists of three main components:

### 1. **AnimationManager**
```python
class AnimationManager
```
- Loads sprite animations from the file system
- Manages 24-frame animation sequences for each action
- Provides frame-by-frame access to sprites

### 2. **FoxyBrain**
```python
class FoxyBrain
```
- Implements the reinforcement learning algorithm
- Maintains action weights and statistics
- Handles persistence (saving/loading brain state)
- Chooses actions using epsilon-greedy strategy

**Key Methods**:
- `choose_action()` - Selects next action based on weights
- `give_feedback(action, positive)` - Updates weights based on user interaction
- `save_brain()` / `load_brain()` - Persists learning state

### 3. **FoxyWidget**
```python
class FoxyWidget(QWidget)
```
- PyQt5 widget that displays Foxy on screen
- Handles animation playback (24 FPS)
- Manages user interactions (clicks and dragging)
- Coordinates between animations and brain

**Key Features**:
- Frameless, transparent window
- Always on top
- Draggable positioning
- Click detection for feedback

---

## 🧠 Learning Algorithm

### Weight-Based Action Selection

#### Initial State
```python
weights = {
    'excited': 1.0,
    'relax': 1.0,
    'sleep': 1.0,
    'walk': 1.0
}
```

All actions are equally likely (25% each).

#### After User Interaction

**Positive Feedback (Click)**:
```python
weight += 0.15  # Increase by 15%
```

**Negative Feedback (Ignore)**:
```python
weight -= 0.05  # Decrease by 5%
weight = max(0.1, weight)  # Minimum weight is 0.1
```

#### Example Learning Scenario

**Initial State**:
```
All weights = 1.0
Each action has 25% probability
```

**User clicks "excited" 3 times, ignores "relax" 2 times**:
```
excited: 1.0 + (0.15 × 3) = 1.45
walk:    1.0 + (0.15 × 1) = 1.15
sleep:   1.0 - (0.05 × 1) = 0.95
relax:   1.0 - (0.05 × 2) = 0.90

New probabilities:
- excited: 33.3% ← Most likely
- walk:    26.4%
- sleep:   21.8%
- relax:   18.5% ← Least likely
```

### Probability Calculation

```python
total_weight = sum(all weights)
probability = action_weight / total_weight

# Weighted random selection
rand = random()
cumulative = 0
for action, prob in probabilities:
    cumulative += prob
    if rand <= cumulative:
        return action
```

### Why Asymmetric Learning Rates?

- **Positive feedback** (+0.15) is **3x stronger** than negative (-0.05)
- **Reason**: Clicks are explicit signals, ignoring might be accidental
- **Effect**: Prevents rapid unlearning of good behaviors

---

## 🎨 Customization

### Adjust Learning Speed

```python
# In FoxyBrain.__init__()
self.learning_rate_positive = 0.15  # Higher = learns faster from clicks
self.learning_rate_negative = 0.05  # Higher = forgets faster when ignored
```

### Change Exploration Rate

```python
# In FoxyBrain.__init__()
self.exploration_rate = 0.3  # 0.0 = no exploration, 1.0 = always random
```

### Modify Action Timing

```python
# In FoxyWidget.__init__()
self.min_idle_duration = 48     # Minimum rest (frames) - 2 sec
self.max_idle_duration = 240    # Maximum rest (frames) - 10 sec
self.action_frame_duration = 72 # Action length (frames) - 3 sec
```

### Adjust Pet Size

```python
# In FoxyWidget.__init__()
self.scale_factor = 0.2  # 0.1 = tiny, 0.5 = large, 1.0 = original size
```

### Change Frame Rate

```python
# In FoxyWidget.__init__()
self.fps = 24  # Frames per second (standard: 24)
```

---

## 📁 File Structure

```
foxy-vpet/
├── foxy_vpet.py              # Main application
├── foxy_brain.json           # Learning state (auto-generated)
├── README.md                 # This file
└── animations/               # Animation sprite folders
    ├── idle/
    │   ├── idle_00.png
    │   ├── idle_01.png
    │   ├── ...
    │   └── idle_23.png       # 24 frames total
    ├── excited/
    │   ├── excited_00.png
    │   └── ...
    ├── relax/
    │   ├── relax_00.png
    │   └── ...
    ├── sleep/
    │   ├── sleep_00.png
    │   └── ...
    └── walk/
        ├── walk_00.png
        └── ...
```

### Brain State File (`foxy_brain.json`)

```json
{
  "weights": {
    "excited": 1.35,
    "relax": 0.95,
    "sleep": 0.80,
    "walk": 1.20
  },
  "action_counts": {
    "excited": 15,
    "relax": 12,
    "sleep": 8,
    "walk": 14
  },
  "positive_feedback": {
    "excited": 10,
    "relax": 4,
    "sleep": 1,
    "walk": 7
  }
}
```

**Fields**:
- `weights` - Current probability weights for each action
- `action_counts` - Total times each action was performed
- `positive_feedback` - Number of clicks received per action

---

## 🐛 Troubleshooting

### Issue: Foxy always does the same action

**Solution**:
- Delete `foxy_brain.json` to reset learning
- Increase `exploration_rate` for more variety:
  ```python
  self.exploration_rate = 0.5  # 50% exploration
  ```

### Issue: Animations not loading

**Solution**:
- Verify `animations/` folder exists in the same directory as `foxy_vpet.py`
- Check frame naming: `{action}_00.png` through `{action}_23.png`
- Look for console warnings: `Warning: Missing frame ...`
- Ensure PNG files are not corrupted

### Issue: Brain not learning

**Solution**:
- Make sure you're clicking **during** the action (not during idle)
- Check that `foxy_brain.json` is being created and updated
- Verify write permissions in the application directory
- Look for console output showing feedback:
  ```
  ✓ Positive feedback for 'excited' - New weight: 1.15
  ```

### Issue: Foxy won't stay on top

**Solution**:
- Check your window manager settings
- Some systems may override `Qt.WindowStaysOnTopHint`
- Try running with elevated permissions (not recommended)

### Issue: Can't drag Foxy

**Solution**:
- Ensure you're clicking directly on the fox sprite (not transparent area)
- Try clicking and holding, then moving the mouse

---

## 📊 Console Output

### Startup
```
Loaded 24 frames for idle
Loaded 24 frames for excited
Loaded 24 frames for relax
Loaded 24 frames for sleep
Loaded 24 frames for walk
Brain loaded from file!

=== Foxy VPET Started ===
Click on Foxy when it does something you like!
Foxy will learn what gets your attention over time.
```

### During Operation
```
Starting action: idle
🔍 Exploring: chose 'excited' randomly
Starting action: excited
User clicked during 'excited'!
✓ Positive feedback for 'excited' - New weight: 1.15
Starting action: idle
🧠 Exploiting: chose 'walk' from learned weights
Starting action: walk
✗ Negative feedback for 'walk' - New weight: 0.95
```

---

## 🚀 Future Enhancement Ideas

- [ ] **Context Awareness**: Learn different behaviors for time of day
- [ ] **Action Sequences**: Chain multiple actions together
- [ ] **Mood System**: Internal state affecting action selection
- [ ] **Sound Effects**: Audio feedback for actions
- [ ] **Multiple Pets**: Run several pets with shared learning
- [ ] **Advanced RL**: Implement Q-learning or policy gradients
- [ ] **Custom Skins**: User-provided sprite sets
- [ ] **Statistics Dashboard**: Visualize learning progress

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with PyQt5
- Inspired by classic desktop pets (Tamagotchi, eSheep, etc.)
- Reinforcement learning concepts from sutton & Barto's RL textbook

---

## 📧 Contact

Project Link: [https://github.com/yourusername/foxy-vpet](https://github.com/yourusername/foxy-vpet)

---

**Made with ❤️ and 🦊**
