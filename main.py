import sys
import random
import os
import time
import math
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect, QSize
from PyQt5.QtGui import QPixmap, QBitmap, QPainter, QRegion, QImage, QCursor, QTransform, QPen, QColor
from PyQt5.QtWidgets import QApplication, QWidget, QMenu, QDialog


class PetConfig:
    """Configuration constants for the virtual pet"""
    FPS = 24
    FRAMES_PER_ANIMATION = 24
    SCALE_FACTOR = 0.2
    STEP_SIZES = {'walk': 2, 'run': 10}
    DOUBLE_CLICK_THRESHOLD = 0.4
    AI_UPDATE_INTERVAL = 3000
    ANIMATION_STATES = {
        'idle': {'weight': 0.3, 'loop': True},
        'walk': {'weight': 0.5, 'loop': True},
        'sleep': {'weight': 0.1, 'loop': True},
        'eat': {'weight': 0.1, 'loop': False},
        'excited': {'weight': 0.0, 'loop': False},
        'drag': {'weight': 0.0, 'loop': True},
        'run': {'weight': 0.0, 'loop': True}
    }


class VirtualPet(QWidget):
    def __init__(self):
        super().__init__()
        
        # Animation configuration
        self.fps = PetConfig.FPS
        self.frame_duration = 1000 // self.fps  # ~42ms per frame
        self.animations_root = "animations"
        self.animation_states = PetConfig.ANIMATION_STATES
        
        # Load animations
        self.animations = self.load_all_animations()
        
        # Pet state
        self.state = 'idle'
        self.current_frame = 0
        self.direction = 1
        self.is_moving = False
        self.target_pos = None
        
        # Initialize window
        self.init_window()
        
        # Initialize timers
        self.init_timers()
        
        # Mouse interaction state
        self.drag_start_pos = None
        self.last_click_time = 0
        self.click_count = 0

        # Control space (pet movement boundary)
        self.control_space = QApplication.primaryScreen().availableGeometry()

    def init_window(self):
        """Initialize the pet window"""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.PointingHandCursor)
        
        # Set window size and position
        screen = QApplication.primaryScreen().availableGeometry()
        side = max(self.max_frame_size.width(), self.max_frame_size.height())
        self.resize(side, side)
        self.move(
            random.randint(100, screen.width() - 200),
            random.randint(100, screen.height() - 200)
        )
        
        self.update_window_mask()

    def init_timers(self):
        """Initialize animation and AI timers"""
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(self.frame_duration)
        
        self.ai_timer = QTimer()
        self.ai_timer.timeout.connect(self.update_behavior)
        self.ai_timer.start(PetConfig.AI_UPDATE_INTERVAL)

    def load_all_animations(self):
        """Load all animation frames from disk"""
        animations = {}
        self.max_frame_size = QSize(0, 0)

        for state in self.animation_states:
            frames = self.load_animation_frames(state)
            animations[state] = frames

        return animations

    def load_animation_frames(self, state):
        """Load frames for a specific animation state"""
        folder_path = os.path.join(self.animations_root, state)
        frames = []

        try:
            if not os.path.exists(folder_path):
                raise FileNotFoundError(f"Animation folder not found: {folder_path}")

            # Get all PNG files and sort them by frame number
            frame_files = [f for f in os.listdir(folder_path) if f.endswith('.png')]
            frame_files.sort(key=lambda x: self.extract_frame_number(x))

            if len(frame_files) != PetConfig.FRAMES_PER_ANIMATION:
                print(f"Warning: Expected {PetConfig.FRAMES_PER_ANIMATION} frames in '{folder_path}', found {len(frame_files)}")

            # Load exactly 24 frames (or as many as available)
            for i in range(min(PetConfig.FRAMES_PER_ANIMATION, len(frame_files))):
                frame_path = os.path.join(folder_path, frame_files[i])
                pixmap = self.load_and_scale_frame(frame_path)
                if pixmap:
                    frames.append(pixmap)

            # If we have fewer than 24 frames, use the last frame to fill
            while len(frames) < PetConfig.FRAMES_PER_ANIMATION:
                if frames:
                    frames.append(frames[-1])
                else:
                    frames.append(self.create_placeholder_frame())

        except Exception as e:
            print(f"Error loading animations from {folder_path}: {e}")
            frames = [self.create_placeholder_frame()] * PetConfig.FRAMES_PER_ANIMATION

        return frames

    def extract_frame_number(self, filename):
        """Extract frame number from filename for sorting"""
        try:
            # Assumes format like "frame_01.png" or "animation_05.png"
            parts = filename.split('_')
            if len(parts) >= 2:
                return int(parts[1].split('.')[0])
            return 0
        except (ValueError, IndexError):
            return 0

    def load_and_scale_frame(self, frame_path):
        """Load and scale a single frame"""
        try:
            pixmap = QPixmap(frame_path)
            if pixmap.isNull():
                print(f"Warning: Could not load image {frame_path}")
                return None

            scaled_pixmap = pixmap.scaled(
                int(pixmap.width() * PetConfig.SCALE_FACTOR),
                int(pixmap.height() * PetConfig.SCALE_FACTOR),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            # Update max frame size
            self.max_frame_size.setWidth(max(self.max_frame_size.width(), scaled_pixmap.width()))
            self.max_frame_size.setHeight(max(self.max_frame_size.height(), scaled_pixmap.height()))

            return scaled_pixmap
        except Exception as e:
            print(f"Error loading frame {frame_path}: {e}")
            return None

    def create_placeholder_frame(self):
        """Create a simple placeholder frame when animation loading fails"""
        pixmap = QPixmap(100, 100)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setPen(QPen(Qt.red, 2))
        painter.drawEllipse(10, 10, 80, 80)
        painter.drawText(25, 55, "PET")
        painter.end()
        return pixmap

    def update_window_mask(self):
        """Update the window mask based on current frame's alpha channel"""
        if not self.animations or self.state not in self.animations:
            return
            
        current_frame = self.animations[self.state][self.current_frame]
        alpha_mask = current_frame.toImage().createAlphaMask()
        region = QRegion(QBitmap.fromImage(alpha_mask))

        offset_x = (self.width() - current_frame.width()) // 2
        offset_y = (self.height() - current_frame.height()) // 2
        self.setMask(region.translated(offset_x, offset_y))

    def update_animation(self):
        """Update the current animation frame"""
        if self.state not in self.animations:
            return
            
        frames = self.animations[self.state]
        state_config = self.animation_states[self.state]
        
        if state_config['loop'] or self.current_frame < len(frames) - 1:
            self.current_frame = (self.current_frame + 1) % len(frames)
        else:
            # Non-looping animation finished, return to idle
            self.change_state('idle')
        
        self.update_window_mask()
        self.update()
        
        # Handle movement for walking/running states
        if self.state in ['walk', 'run'] and self.is_moving:
            self.move_toward_target()

    def update_behavior(self):
        """AI behavior update - randomly change states"""
        # Don't interrupt certain states
        if self.state in ['eat', 'excited', 'drag']:
            return
            
        if random.random() < 0.3:
            available_states = [s for s in self.animation_states.keys() 
                              if s not in ['excited', 'drag']]
            weights = [self.animation_states[s]['weight'] for s in available_states]
            new_state = random.choices(available_states, weights=weights, k=1)[0]
            self.change_state(new_state)

    def change_state(self, new_state, force=False):
        """Change the pet's animation state"""
        if new_state == self.state and not force:
            return
            
        # Clean up previous state
        if self.state == 'drag':
            self.setCursor(Qt.PointingHandCursor)
        
        self.state = new_state
        self.current_frame = 0
        
        # Initialize new state
        if new_state in ['walk', 'run']:
            self.setup_movement_state()
        else:
            self.cleanup_movement_state()

    def setup_movement_state(self):
        """Setup state for walking/running"""
        if not self.target_pos:
            # Pick a random target within control space
            margin = 50
            self.target_pos = QPoint(
                random.randint(self.control_space.left() + margin, 
                             self.control_space.right() - margin),
                random.randint(self.control_space.top() + margin, 
                             self.control_space.bottom() - margin)
            )
        
        self.is_moving = True
        self.direction = 1 if self.target_pos.x() > self.pos().x() else -1

    def cleanup_movement_state(self):
        """Clean up movement-related state"""
        self.is_moving = False
        self.target_pos = None

    def move_toward_target(self):
        """Move the pet toward its target position with smooth movement"""
        if not self.target_pos:
            return

        current_pos = self.pos()
        diff = self.target_pos - current_pos
        distance = math.sqrt(diff.x()**2 + diff.y()**2)
        
        # Stop if we're close enough
        step_size = PetConfig.STEP_SIZES.get(self.state, 2)
        if distance < step_size:
            self.change_state('idle')
            return
        
        # Calculate normalized movement
        move_x = int(diff.x() / distance * step_size) if distance > 0 else 0
        move_y = int(diff.y() / distance * step_size) if distance > 0 else 0
        
        new_pos = current_pos + QPoint(move_x, move_y)
        clamped_pos = self.clamp_to_control_space(new_pos)
        
        # If we can't move (hit boundary), stop
        if clamped_pos == current_pos:
            self.change_state('idle')
            return
            
        self.move(clamped_pos)

    def clamp_to_control_space(self, pos):
        """Clamp position to stay within control space"""
        new_x = min(max(self.control_space.left(), pos.x()), 
                   self.control_space.right() - self.width())
        new_y = min(max(self.control_space.top(), pos.y()), 
                   self.control_space.bottom() - self.height())
        return QPoint(new_x, new_y)

    def paintEvent(self, event):
        """Paint the current animation frame"""
        painter = QPainter(self)
        
        if self.state not in self.animations:
            return
            
        current_frame = self.animations[self.state][self.current_frame]
        
        # Flip frame horizontally if facing left
        if self.direction == -1:
            current_frame = current_frame.transformed(QTransform().scale(-1, 1))
        
        # Center the frame in the widget
        x = (self.width() - current_frame.width()) // 2
        y = (self.height() - current_frame.height()) // 2
        painter.drawPixmap(x, y, current_frame)

    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.globalPos() - self.pos()
            
            # Handle double-click detection
            current_time = time.monotonic()
            if current_time - self.last_click_time < PetConfig.DOUBLE_CLICK_THRESHOLD:
                self.click_count += 1
                if self.click_count >= 2:
                    self.change_state('excited')
                    QTimer.singleShot(1000, self.jump_to_cursor)
            else:
                self.click_count = 1
            self.last_click_time = current_time
            
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        """Handle mouse move events (dragging)"""
        if self.drag_start_pos is not None:
            self.move(event.globalPos() - self.drag_start_pos)
            if self.state != 'drag':
                self.change_state('drag')

    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = None
            self.setCursor(Qt.PointingHandCursor)
            
            if self.state == 'drag':
                # Ensure pet is within control space after dragging
                pet_rect = QRect(self.pos(), self.size())
                if not self.control_space.contains(pet_rect):
                    clamped_pos = self.clamp_to_control_space(self.pos())
                    self.move(clamped_pos)
                self.change_state('idle')

    def jump_to_cursor(self):
        """Make the pet jump/run to the cursor position"""
        cursor_pos = QCursor.pos()
        pet_size = self.size()
        
        # Calculate target position (try to center pet on cursor)
        target_rect = QRect(cursor_pos - QPoint(pet_size.width()//2, pet_size.height()//2), pet_size)
        
        if self.control_space.contains(target_rect):
            target = target_rect.topLeft()
        else:
            target = self.clamp_to_control_space(cursor_pos)
        
        self.target_pos = target
        self.direction = 1 if self.target_pos.x() > self.pos().x() else -1
        self.is_moving = True
        self.change_state('run')

    def edit_control_space(self):
        """Open the control space editor"""
        pet_rect = QRect(self.pos(), self.size())
        self.control_editor = ControlSpaceEditor(self.control_space, self.set_control_space, pet_rect)

    def set_control_space(self, rect, teleport_pos=None):
        """Set new control space and optionally teleport pet"""
        self.control_space = rect
        if teleport_pos:
            self.move(teleport_pos)
        print(f"Updated control space: {rect}")
        if teleport_pos:
            print(f"Pet moved to: {self.pos()}")

    def contextMenuEvent(self, event):
        """Handle right-click context menu"""
        menu = QMenu(self)
        settings_menu = menu.addMenu("Settings")
        control_space_action = settings_menu.addAction("Edit Control Space")
        exit_action = settings_menu.addAction("Exit Pet")
        
        chosen_action = menu.exec_(self.mapToGlobal(event.pos()))

        if chosen_action == exit_action:
            self.close()
        elif chosen_action == control_space_action:
            self.edit_control_space()


class ControlSpaceEditor(QDialog):
    """Dialog for editing the pet's movement boundary"""
    
    def __init__(self, initial_rect, callback, pet_rect: QRect):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setMouseTracking(True)

        self.start_pos = None
        self.selection_rect = QRect()
        self.initial_rect = initial_rect
        self.callback = callback
        self.pet_rect = pet_rect
        self.dragging = False

        # Cover entire screen
        self.setGeometry(QApplication.primaryScreen().geometry())
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def paintEvent(self, event):
        """Paint the control space editor overlay"""
        painter = QPainter(self)
        
        # Semi-transparent background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 128))

        # Existing control space (dashed red box)
        painter.setPen(QPen(Qt.red, 2, Qt.DashLine))
        painter.drawRect(self.initial_rect)

        # Current selection box (solid red box)
        if not self.selection_rect.isEmpty():
            painter.setPen(QPen(Qt.red, 3))
            painter.drawRect(self.selection_rect)

        # Pet current position (green border)
        painter.setPen(QPen(Qt.green, 2))
        painter.drawRect(self.pet_rect)
        
        # Instructions text
        painter.setPen(QPen(Qt.white, 1))
        painter.drawText(20, 30, "Drag to define new control space. Green box shows pet position.")
        painter.drawText(20, 50, "Red dashed box shows current control space.")

    def mousePressEvent(self, event):
        """Start dragging to define new control space"""
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.dragging = True
            self.selection_rect = QRect()

    def mouseMoveEvent(self, event):
        """Update selection rectangle while dragging"""
        if self.dragging and self.start_pos:
            end_pos = event.pos()
            x1, y1 = self.start_pos.x(), self.start_pos.y()
            x2, y2 = end_pos.x(), end_pos.y()
            self.selection_rect = QRect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            self.update()

    def mouseReleaseEvent(self, event):
        """Finalize control space selection"""
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False

            if self.selection_rect.isEmpty():
                self.close()
                return

            # Ensure rectangle is large enough for the pet
            min_width = self.pet_rect.width() + 40
            min_height = self.pet_rect.height() + 40

            if (self.selection_rect.width() < min_width or 
                self.selection_rect.height() < min_height):
                center = self.selection_rect.center()
                self.selection_rect.setSize(QSize(
                    max(min_width, self.selection_rect.width()),
                    max(min_height, self.selection_rect.height())
                ))
                self.selection_rect.moveCenter(center)

            # Check if pet needs to be teleported
            teleport_pos = None
            if not self.selection_rect.contains(self.pet_rect):
                # Calculate new position near center of control space
                new_x = max(self.selection_rect.left(),
                           min(self.selection_rect.right() - self.pet_rect.width(),
                               self.selection_rect.center().x() - self.pet_rect.width()//2))
                new_y = max(self.selection_rect.top(),
                           min(self.selection_rect.bottom() - self.pet_rect.height(),
                               self.selection_rect.center().y() - self.pet_rect.height()//2))
                teleport_pos = QPoint(new_x, new_y)

            # Apply the new control space
            self.callback(self.selection_rect, teleport_pos)
            self.close()

    def keyPressEvent(self, event):
        """Handle escape key to cancel"""
        if event.key() == Qt.Key_Escape:
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = VirtualPet()
    pet.show()
    sys.exit(app.exec_())