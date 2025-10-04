import sys
import os
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QCursor
import random
import json

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
            
            # Load 24 frames (00 to 23)
            for i in range(24):
                frame_path = os.path.join(action_path, f"{action}_{i:02d}.png")
                if os.path.exists(frame_path):
                    frames.append(frame_path)
                else:
                    print(f"Warning: Missing frame {frame_path}")
            
            if frames:
                self.animations[action] = frames
                print(f"Loaded {len(frames)} frames for {action}")
    
    def get_frame(self, action, frame_index):
        """Get a specific frame for an action"""
        if action in self.animations:
            frames = self.animations[action]
            return frames[frame_index % len(frames)]
        return None


class FoxyBrain:
    """Reinforcement learning brain for Foxy"""
    
    def __init__(self, save_file="foxy_brain.json"):
        self.save_file = save_file
        self.actions = ['excited', 'relax', 'sleep', 'walk']
        
        # Initialize weights (excluding idle - it's default)
        self.weights = {action: 1.0 for action in self.actions}
        self.action_counts = {action: 0 for action in self.actions}
        self.positive_feedback = {action: 0 for action in self.actions}
        
        self.learning_rate_positive = 0.15  # Increase weight on click
        self.learning_rate_negative = 0.05  # Decrease weight on ignore
        
        # Exploration rate (epsilon-greedy)
        self.exploration_rate = 0.5  # 50% random exploration, 50% exploitation
        
        self.load_brain()
    
    def choose_action(self):
        """Choose an action based on current weights with epsilon-greedy exploration"""
        
        # 50% of the time: explore randomly
        if random.random() < self.exploration_rate:
            action = random.choice(self.actions)
            print(f"🔍 Exploring: chose '{action}' randomly")
            return action
        
        # 50% of the time: exploit learned weights
        total_weight = sum(self.weights.values())
        
        # Normalize weights to probabilities
        probabilities = {action: weight/total_weight 
                        for action, weight in self.weights.items()}
        
        # Random choice based on weights
        rand_val = random.random()
        cumulative = 0
        
        for action, prob in probabilities.items():
            cumulative += prob
            if rand_val <= cumulative:
                print(f"🧠 Exploiting: chose '{action}' from learned weights")
                return action
        
        return random.choice(self.actions)
    
    def give_feedback(self, action, positive=True):
        """Update weights based on user interaction"""
        if action not in self.actions:
            return
        
        self.action_counts[action] += 1
        
        if positive:
            # User clicked - reinforce this action
            self.weights[action] += self.learning_rate_positive
            self.positive_feedback[action] += 1
            print(f"✓ Positive feedback for '{action}' - New weight: {self.weights[action]:.2f}")
        else:
            # User ignored - decrease this action
            self.weights[action] = max(0.1, self.weights[action] - self.learning_rate_negative)
            print(f"✗ Negative feedback for '{action}' - New weight: {self.weights[action]:.2f}")
        
        self.save_brain()
    
    def save_brain(self):
        """Save brain state to file"""
        data = {
            'weights': self.weights,
            'action_counts': self.action_counts,
            'positive_feedback': self.positive_feedback
        }
        
        with open(self.save_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_brain(self):
        """Load brain state from file"""
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, 'r') as f:
                    data = json.load(f)
                    self.weights = data.get('weights', self.weights)
                    self.action_counts = data.get('action_counts', self.action_counts)
                    self.positive_feedback = data.get('positive_feedback', self.positive_feedback)
                    print("Brain loaded from file!")
            except Exception as e:
                print(f"Error loading brain: {e}")
    
    def get_stats(self):
        """Get statistics about the brain's learning"""
        return {
            'weights': self.weights,
            'action_counts': self.action_counts,
            'positive_feedback': self.positive_feedback
        }


class FoxyWidget(QWidget):
    """The visual desktop pet widget"""
    
    def __init__(self, animation_manager, brain):
        super().__init__()
        self.animation_manager = animation_manager
        self.brain = brain
        
        # Setup widget
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Setup label for displaying fox
        self.label = QLabel(self)
        
        # Scale factor for pet size
        self.scale_factor = 0.1  # 10% of original size
        
        # Animation state
        self.current_action = 'idle'
        self.current_frame = 0
        self.fps = 24
        
        # Action timing
        self.action_duration = 0  # Frames remaining for current action
        self.min_idle_duration = 48  # 2 seconds of idle (24fps * 2)
        self.max_idle_duration = 240  # 10 seconds of idle
        self.action_frame_duration = 72  # 3 seconds (24fps * 3 = 72 frames)
        
        # User interaction tracking
        self.user_clicked_during_action = False
        self.current_non_idle_action = None
        
        # Position
        self.drag_position = None
        self.setGeometry(100, 100, 150, 150)
        
        # Animation timer (24 FPS)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(1000 // self.fps)
        
        # Start with idle
        self.start_action('idle')
    
    def start_action(self, action):
        """Start a new action"""
        self.current_action = action
        self.current_frame = 0
        self.user_clicked_during_action = False
        
        if action == 'idle':
            # Random idle duration
            self.action_duration = random.randint(self.min_idle_duration, self.max_idle_duration)
            self.current_non_idle_action = None
        else:
            # Non-idle actions last 1 loop (24 frames)
            self.action_duration = self.action_frame_duration
            self.current_non_idle_action = action
        
        print(f"Starting action: {action}")
    
    def update_animation(self):
        """Update animation frame"""
        # Get current frame
        frame_path = self.animation_manager.get_frame(self.current_action, self.current_frame)
        
        if frame_path:
            pixmap = QPixmap(frame_path)
            
            # Scale down to 10% of original size
            scaled_width = int(pixmap.width() * self.scale_factor)
            scaled_height = int(pixmap.height() * self.scale_factor)
            
            scaled_pixmap = pixmap.scaled(
                scaled_width,
                scaled_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.label.setPixmap(scaled_pixmap)
            self.label.resize(scaled_pixmap.size())
            self.resize(scaled_pixmap.size())
        
        # Advance frame
        self.current_frame = (self.current_frame + 1) % 24
        self.action_duration -= 1
        
        # Check if action is complete
        if self.action_duration <= 0:
            self.finish_action()
    
    def finish_action(self):
        """Finish current action and decide next one"""
        # Give feedback if it was a non-idle action
        if self.current_non_idle_action:
            self.brain.give_feedback(
                self.current_non_idle_action, 
                positive=self.user_clicked_during_action
            )
        
        # Decide next action
        if self.current_action == 'idle':
            # After idle, choose a new action
            next_action = self.brain.choose_action()
            self.start_action(next_action)
        else:
            # After non-idle action, return to idle
            self.start_action('idle')
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging and clicking"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            
            # Register click for feedback
            if self.current_non_idle_action:
                self.user_clicked_during_action = True
                print(f"User clicked during '{self.current_non_idle_action}'!")
            
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
    
    # Initialize components
    animation_manager = AnimationManager("animations")
    brain = FoxyBrain("foxy_brain.json")
    
    # Create Foxy
    foxy = FoxyWidget(animation_manager, brain)
    foxy.show()
    
    print("\n=== Foxy VPET Started ===")
    print("Click on Foxy when it does something you like!")
    print("Foxy will learn what gets your attention over time.\n")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()