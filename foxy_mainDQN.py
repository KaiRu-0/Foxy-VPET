import sys
import os
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap
import random
import json
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque


class DQNNetwork(nn.Module):
    """Deep Q-Network for action selection"""
    
    def __init__(self, state_size, action_size, hidden_size=64):
        super(DQNNetwork, self).__init__()
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, action_size)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)


class ReplayBuffer:
    """Experience replay buffer for DQN"""
    
    def __init__(self, capacity=1000):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size):
        batch = random.sample(self.buffer, min(batch_size, len(self.buffer)))
        states, actions, rewards, next_states, dones = zip(*batch)
        return (np.array(states), np.array(actions), np.array(rewards),
                np.array(next_states), np.array(dones))
    
    def __len__(self):
        return len(self.buffer)


class FoxyBrainDQN:
    """Deep Q-Learning brain for Foxy"""
    
    def __init__(self, save_dir="foxy_model"):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        
        self.actions = ['excited', 'relax', 'sleep', 'walk']
        self.action_to_idx = {action: idx for idx, action in enumerate(self.actions)}
        self.idx_to_action = {idx: action for action, idx in self.action_to_idx.items()}
        
        # State: [time_of_day, last_click_recency, action_count_normalized, ...]
        self.state_size = 8  # Enhanced state representation
        self.action_size = len(self.actions)
        
        # DQN hyperparameters
        self.gamma = 0.95  # Discount factor
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_min = 0.1
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001
        self.batch_size = 32
        
        # Networks
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.policy_net = DQNNetwork(self.state_size, self.action_size).to(self.device)
        self.target_net = DQNNetwork(self.state_size, self.action_size).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=self.learning_rate)
        self.criterion = nn.MSELoss()
        
        # Experience replay
        self.memory = ReplayBuffer(capacity=2000)
        
        # Statistics
        self.action_counts = {action: 0 for action in self.actions}
        self.positive_feedback = {action: 0 for action in self.actions}
        self.total_clicks = 0
        self.total_actions = 0
        self.last_click_time = 0
        self.current_time = 0
        
        # Current state tracking
        self.current_state = None
        self.current_action_idx = None
        
        self.load_brain()
    
    def get_state(self):
        """Create state representation"""
        # Normalize time (0-1 for 24-hour cycle simulation)
        time_normalized = (self.current_time % 1000) / 1000.0
        
        # Time since last click (capped at 500)
        recency = min((self.current_time - self.last_click_time) / 500.0, 1.0)
        
        # Click rate
        click_rate = self.total_clicks / max(self.total_actions, 1)
        
        # Action distribution (normalized counts)
        total_count = sum(self.action_counts.values()) + 1
        action_dist = [self.action_counts[action] / total_count for action in self.actions]
        
        # Success rate per action
        success_rate = self.positive_feedback.get(self.actions[0], 0) / max(self.action_counts.get(self.actions[0], 1), 1)
        
        state = [time_normalized, recency, click_rate, success_rate] + action_dist
        return np.array(state, dtype=np.float32)
    
    def choose_action(self):
        """Choose action using epsilon-greedy policy"""
        self.current_time += 1
        self.current_state = self.get_state()
        
        # Epsilon-greedy exploration
        if random.random() < self.epsilon:
            action_idx = random.randint(0, self.action_size - 1)
            print(f"🔍 Exploring: chose '{self.idx_to_action[action_idx]}' (ε={self.epsilon:.3f})")
        else:
            with torch.no_grad():
                state_tensor = torch.FloatTensor(self.current_state).unsqueeze(0).to(self.device)
                q_values = self.policy_net(state_tensor)
                action_idx = q_values.argmax().item()
                print(f"🧠 Exploiting: chose '{self.idx_to_action[action_idx]}' (Q={q_values[0][action_idx]:.3f})")
        
        self.current_action_idx = action_idx
        action = self.idx_to_action[action_idx]
        self.action_counts[action] += 1
        self.total_actions += 1
        
        return action
    
    def give_feedback(self, action, positive=True):
        """Update model based on user interaction"""
        if action not in self.actions:
            return
        
        action_idx = self.action_to_idx[action]
        
        # Calculate reward
        if positive:
            reward = 1.0  # Positive reward for click
            self.positive_feedback[action] += 1
            self.total_clicks += 1
            self.last_click_time = self.current_time
            print(f"✓ Positive feedback for '{action}' - Reward: +1.0")
        else:
            reward = -0.1  # Small negative reward for ignore
            print(f"✗ Negative feedback for '{action}' - Reward: -0.1")
        
        # Get next state
        next_state = self.get_state()
        done = False
        
        # Store experience
        if self.current_state is not None:
            self.memory.push(self.current_state, action_idx, reward, next_state, done)
        
        # Train the network
        self.train()
        
        # Decay epsilon
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        
        self.save_brain()
    
    def train(self):
        """Train the DQN using experience replay"""
        if len(self.memory) < self.batch_size:
            return
        
        # Sample batch
        states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)
        
        # Convert to tensors
        states = torch.FloatTensor(states).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(next_states).to(self.device)
        dones = torch.FloatTensor(dones).to(self.device)
        
        # Current Q values
        current_q = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        
        # Next Q values
        with torch.no_grad():
            next_q = self.target_net(next_states).max(1)[0]
            target_q = rewards + (1 - dones) * self.gamma * next_q
        
        # Compute loss and update
        loss = self.criterion(current_q, target_q)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        # Update target network periodically
        if self.total_actions % 100 == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())
            print(f"🔄 Target network updated (Loss: {loss.item():.4f})")
    
    def save_brain(self):
        """Save model and statistics"""
        # Save model
        torch.save({
            'policy_net': self.policy_net.state_dict(),
            'target_net': self.target_net.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
        }, os.path.join(self.save_dir, 'model.pth'))
        
        # Save statistics
        stats = {
            'action_counts': self.action_counts,
            'positive_feedback': self.positive_feedback,
            'total_clicks': self.total_clicks,
            'total_actions': self.total_actions,
            'last_click_time': self.last_click_time,
            'current_time': self.current_time,
        }
        with open(os.path.join(self.save_dir, 'stats.json'), 'w') as f:
            json.dump(stats, f, indent=2)
    
    def load_brain(self):
        """Load model and statistics"""
        model_path = os.path.join(self.save_dir, 'model.pth')
        stats_path = os.path.join(self.save_dir, 'stats.json')
        
        if os.path.exists(model_path):
            try:
                checkpoint = torch.load(model_path, map_location=self.device)
                self.policy_net.load_state_dict(checkpoint['policy_net'])
                self.target_net.load_state_dict(checkpoint['target_net'])
                self.optimizer.load_state_dict(checkpoint['optimizer'])
                self.epsilon = checkpoint['epsilon']
                print("🧠 Model loaded from checkpoint!")
            except Exception as e:
                print(f"Error loading model: {e}")
        
        if os.path.exists(stats_path):
            try:
                with open(stats_path, 'r') as f:
                    stats = json.load(f)
                    self.action_counts = stats.get('action_counts', self.action_counts)
                    self.positive_feedback = stats.get('positive_feedback', self.positive_feedback)
                    self.total_clicks = stats.get('total_clicks', 0)
                    self.total_actions = stats.get('total_actions', 0)
                    self.last_click_time = stats.get('last_click_time', 0)
                    self.current_time = stats.get('current_time', 0)
                    print("📊 Statistics loaded!")
            except Exception as e:
                print(f"Error loading stats: {e}")
    
    def get_stats(self):
        """Get learning statistics"""
        return {
            'action_counts': self.action_counts,
            'positive_feedback': self.positive_feedback,
            'total_clicks': self.total_clicks,
            'total_actions': self.total_actions,
            'epsilon': self.epsilon,
            'memory_size': len(self.memory),
        }


class AnimationManager:
    """Handles loading and managing fox animations"""
    
    def __init__(self, base_path="animations"):
        self.base_path = base_path
        self.animations = {}
        self.load_animations()
    
    def load_animations(self):
        """Load all animation frames from folders"""
        actions = ['idle', 'excited', 'relax', 'sleep', 'walk']
        
        for action in actions:
            action_path = os.path.join(self.base_path, action)
            frames = []
            
            for i in range(24):
                frame_path = os.path.join(action_path, f"{action}_{i:02d}.png")
                if os.path.exists(frame_path):
                    frames.append(frame_path)
            
            if frames:
                self.animations[action] = frames
                print(f"Loaded {len(frames)} frames for {action}")
    
    def get_frame(self, action, frame_index):
        """Get a specific frame for an action"""
        if action in self.animations:
            frames = self.animations[action]
            return frames[frame_index % len(frames)]
        return None


class FoxyWidget(QWidget):
    """The visual desktop pet widget"""
    
    def __init__(self, animation_manager, brain):
        super().__init__()
        self.animation_manager = animation_manager
        self.brain = brain
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.label = QLabel(self)
        self.scale_factor = 0.2
        
        self.current_action = 'idle'
        self.current_frame = 0
        self.fps = 24
        
        self.action_duration = 0
        self.min_idle_duration = 48
        self.max_idle_duration = 240
        self.action_frame_duration = 72
        
        self.user_clicked_during_action = False
        self.current_non_idle_action = None
        
        self.drag_position = None
        self.setGeometry(100, 100, 150, 150)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(1000 // self.fps)
        
        self.start_action('idle')
    
    def start_action(self, action):
        """Start a new action"""
        self.current_action = action
        self.current_frame = 0
        self.user_clicked_during_action = False
        
        if action == 'idle':
            self.action_duration = random.randint(self.min_idle_duration, self.max_idle_duration)
            self.current_non_idle_action = None
        else:
            self.action_duration = self.action_frame_duration
            self.current_non_idle_action = action
        
        print(f"Starting action: {action}")
    
    def update_animation(self):
        """Update animation frame"""
        frame_path = self.animation_manager.get_frame(self.current_action, self.current_frame)
        
        if frame_path:
            pixmap = QPixmap(frame_path)
            scaled_width = int(pixmap.width() * self.scale_factor)
            scaled_height = int(pixmap.height() * self.scale_factor)
            scaled_pixmap = pixmap.scaled(scaled_width, scaled_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.label.setPixmap(scaled_pixmap)
            self.label.resize(scaled_pixmap.size())
            self.resize(scaled_pixmap.size())
        
        self.current_frame = (self.current_frame + 1) % 24
        self.action_duration -= 1
        
        if self.action_duration <= 0:
            self.finish_action()
    
    def finish_action(self):
        """Finish current action and decide next one"""
        if self.current_non_idle_action:
            self.brain.give_feedback(
                self.current_non_idle_action, 
                positive=self.user_clicked_during_action
            )
        
        if self.current_action == 'idle':
            next_action = self.brain.choose_action()
            self.start_action(next_action)
        else:
            self.start_action('idle')
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging and clicking"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            
            if self.current_non_idle_action:
                self.user_clicked_during_action = True
                print(f"👆 User clicked during '{self.current_non_idle_action}'!")
            
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle dragging"""
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        self.drag_position = None


def main():
    app = QApplication(sys.argv)
    
    animation_manager = AnimationManager("animations")
    brain = FoxyBrainDQN("foxy_model")
    
    foxy = FoxyWidget(animation_manager, brain)
    foxy.show()
    
    print("\n=== Foxy VPET with Deep Q-Learning ===")
    print("🧠 Using PyTorch DQN for reinforcement learning")
    print("👆 Click on Foxy when it does something you like!")
    print("🎯 Foxy will learn optimal behaviors through experience\n")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()