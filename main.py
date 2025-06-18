import sys
import random
import os
import time
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect, QSize
from PyQt5.QtGui import QPixmap, QBitmap, QPainter, QRegion, QImage, QCursor, QTransform, QPen, QColor
from PyQt5.QtWidgets import QApplication, QWidget, QMenu, QDialog

class VirtualPet(QWidget):
	def __init__(self):
		super().__init__()
		
		# Animation configuration
		self.fps = 24
		self.frame_duration = 1000 // self.fps  # ~83ms per frame
		self.animations_root = "animations"
		
		# Available animation states and their properties
		self.animation_states = {
			'idle': {'weight': 0.1, 'loop': True},
			'walk': {'weight': 0.7, 'loop': True},
			'sleep': {'weight': 0.1, 'loop': True},
			'eat': {'weight': 0.1, 'loop': False},
			'excited': {'weight': 0.0, 'loop': False},
			'drag': {'weight': 0.0, 'loop': True}
		}
		
		self.animations = self.load_all_animations()
		
		self.state = 'idle'
		self.current_frame = 0
		self.direction = 1
		self.is_moving = False
		self.target_pos = None
		
		self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
		self.setAttribute(Qt.WA_TranslucentBackground)
		self.update_window_mask()
		self.setCursor(Qt.PointingHandCursor)
		
		screen = QApplication.primaryScreen().availableGeometry()
		self.resize(self.animations['idle'][0].size())
		self.move(
			random.randint(100, screen.width() - 200),
			random.randint(100, screen.height() - 200)
		)
		
		self.animation_timer = QTimer()
		self.animation_timer.timeout.connect(self.update_animation)
		self.animation_timer.start(self.frame_duration)
		
		self.ai_timer = QTimer()
		self.ai_timer.timeout.connect(self.update_behavior)
		self.ai_timer.start(3000)
		
		self.drag_start_pos = None
		self.last_click_time = 0
		self.click_count = 0

		# Controlling Space
		self.control_space = QApplication.primaryScreen().availableGeometry()

	def load_all_animations(self):
		animations = {}
		scale_factor = 2.0
				
		for state in self.animation_states:
			folder_path = os.path.join(self.animations_root, state)
			frames = []
			
			if os.path.exists(folder_path):
				frame_files = sorted(
					[f for f in os.listdir(folder_path) if f.endswith('.png')],
					key=lambda x: int(x.split('_')[1].split('.')[0])
				)

				for frame_file in frame_files:
					frame_path = os.path.join(folder_path, frame_file)
					pixmap = QPixmap(frame_path)
					scaled_pixmap = pixmap.scaled(
						int(pixmap.width() * scale_factor),
						int(pixmap.height() * scale_factor),
						Qt.KeepAspectRatio,
						Qt.SmoothTransformation
                    )
					frames.append(scaled_pixmap)
			else:
				print(f"Warning: Missing animation folder '{folder_path}'")
				os.makedirs(folder_path)
				print(f"Created empty '{folder_path}' - please add animation frames")
			
			if len(frames) < 24:
				print(f"Warning: Only {len(frames)} frames found in '{folder_path}', duplicating to make 24")
				while len(frames) < 24:
					frames.extend(frames[:min(len(frames), 24 - len(frames))])
			
			animations[state] = frames[:24]
		
		return animations

	def update_window_mask(self):
		current_frame = self.animations[self.state][self.current_frame]
		alpha_mask = current_frame.toImage().createAlphaMask()
		region = QRegion(QBitmap.fromImage(alpha_mask))
		self.setMask(region)

	def update_animation(self):
		frames = self.animations[self.state]
		state_config = self.animation_states[self.state]
		
		if state_config['loop'] or self.current_frame < len(frames) - 1:
			self.current_frame = (self.current_frame + 1) % len(frames)
		else:
			self.change_state('idle')
		
		self.update_window_mask()
		self.update()
		
		if self.state == 'walk' and self.is_moving:
			self.move_toward_target()

	def update_behavior(self):
		if self.state in ['eat', 'excited', 'drag']:
			return
			
		if random.random() < 0.3:
			states = [s for s in self.animation_states.keys() if s != 'excited']
			weights = [self.animation_states[s]['weight'] for s in states]
			new_state = random.choices(states, weights=weights, k=1)[0]
			self.change_state(new_state)

	def change_state(self, new_state):
		if new_state != self.state:
			self.state = new_state
			self.current_frame = 0
			
			if self.state == 'walk':
				screen = QApplication.primaryScreen().availableGeometry()
				self.target_pos = QPoint(
					random.randint(50, screen.width() - 100),
					random.randint(50, screen.height() - 100)
				)
				self.is_moving = True
				self.direction = 1 if self.target_pos.x() > self.pos().x() else -1
			else:
				self.is_moving = False
				self.target_pos = None

	def move_toward_target(self):
		if not self.target_pos:
			return

		current_pos = self.pos()
		step_size = 2
		step = QPoint(
			step_size if self.target_pos.x() > current_pos.x() else -step_size,
			step_size if self.target_pos.y() > current_pos.y() else -step_size
		)

		new_pos = current_pos + step

		# Clamp within control space
		new_x = min(max(self.control_space.left(), new_pos.x()), self.control_space.right() - self.width())
		new_y = min(max(self.control_space.top(), new_pos.y()), self.control_space.bottom() - self.height())
		clamped_pos = QPoint(new_x, new_y)

		# If the clamped position is same as current, the pet can't move — stop walking
		if clamped_pos == current_pos:
			self.change_state('idle')
			return

		self.move(clamped_pos)

		# Stop if we are close enough to target
		if (abs(clamped_pos.x() - self.target_pos.x()) < step_size and
			abs(clamped_pos.y() - self.target_pos.y()) < step_size):
			self.change_state('idle')

	

	def paintEvent(self, event):
		painter = QPainter(self)
		current_frame = self.animations[self.state][self.current_frame]
		
		if self.direction == -1:
			current_frame = current_frame.transformed(QTransform().scale(-1, 1))
		
		painter.drawPixmap(0, 0, current_frame)

	def mousePressEvent(self, event):
		if event.button() == Qt.LeftButton:
			self.drag_start_pos = event.globalPos() - self.pos()
			
			current_time = time.monotonic()
			if current_time - self.last_click_time < 0.4:
				self.click_count += 1
				if self.click_count >= 2:
					self.change_state('excited')
					QTimer.singleShot(2000, lambda: self.change_state('idle'))
			else:
				self.click_count = 1
			self.last_click_time = current_time
			
			self.setCursor(Qt.ClosedHandCursor)

	def mouseMoveEvent(self, event):
		if self.drag_start_pos is not None:
			self.move(event.globalPos() - self.drag_start_pos)
			if self.state != 'drag':
				self.change_state('drag')

	def mouseReleaseEvent(self, event):
		if event.button() == Qt.LeftButton:
			self.drag_start_pos = None
			self.setCursor(Qt.PointingHandCursor)
	
			if self.state == 'drag':
				# Check if pet is outside the control space
				pet_rect = QRect(self.pos(), self.size())
				if not self.control_space.contains(pet_rect):
					new_x = min(
						max(self.control_space.left(), self.pos().x()),
						self.control_space.right() - self.width()
					)
					new_y = min(
						max(self.control_space.top(), self.pos().y()),
						self.control_space.bottom() - self.height()
					)
					self.move(new_x, new_y)
	
				self.change_state('idle')

	def edit_control_space(self):
		pet_rect = QRect(self.pos(), self.size())
		self.control_editor = ControlSpaceEditor(self.control_space, self.set_control_space, pet_rect)

	def set_control_space(self, rect, teleport_pos=None):
		self.control_space = rect
		if teleport_pos:
			self.move(teleport_pos)
		print("Updated control space:", rect)
		print("Pet moved to:", self.pos())
	
	def define_control_space(self):
		screen = QApplication.primaryScreen().availableGeometry()
		width = screen.width() // 2
		height = screen.height() // 2
		self.control_space = QRect(100, 100, width, height)
		print("Control space set to:", self.control_space)

	def contextMenuEvent(self, event):
		menu = QMenu(self)
		settings_menu = menu.addMenu("Settings")
		control_space_action = settings_menu.addAction("Control Space")
		exit_action = settings_menu.addAction("Exit Pet")
		chosen_action = menu.exec_(self.mapToGlobal(event.pos()))

		if chosen_action == exit_action:
			self.close()
		elif chosen_action == control_space_action:
			self.edit_control_space()

class ControlSpaceEditor(QDialog):
	def __init__(self, initial_rect, callback, pet_rect: QRect):
		super().__init__()
		self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
		self.setAttribute(Qt.WA_TranslucentBackground)
		self.setAttribute(Qt.WA_NoSystemBackground, True)
		self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
		self.setMouseTracking(True)

		self.start_pos = None
		self.selection_rect = QRect()
		self.initial_rect = initial_rect
		self.callback = callback
		self.pet_rect = pet_rect
		self.dragging = False

		self.setGeometry(QApplication.primaryScreen().geometry())
		self.show()
		self.raise_()
		self.activateWindow()
		self.setFocus()


	def paintEvent(self, event):
		painter = QPainter(self)

		# semi-transparent background
		painter.fillRect(self.rect(), QColor(0, 0, 0, 128))

		# existing control space (faint red box)
		painter.setPen(QPen(Qt.red, 2, Qt.DashLine))
		painter.drawRect(self.initial_rect)

		# current selection box (solid red box)
		painter.setPen(QPen(Qt.red, 2))
		painter.drawRect(self.selection_rect)

		# pet hitbox (green border)
		painter.setPen(QPen(Qt.green, 2))
		painter.drawRect(self.pet_rect)

	def mousePressEvent(self, event):
		if event.button() == Qt.LeftButton:
			self.start_pos = event.pos()
			self.dragging = True

	def mouseMoveEvent(self, event):
		if self.dragging and self.start_pos:
			end_pos = event.pos()
			x1, y1 = self.start_pos.x(), self.start_pos.y()
			x2, y2 = end_pos.x(), end_pos.y()
			self.selection_rect = QRect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
			self.update()

	def mouseReleaseEvent(self, event):
		if event.button() == Qt.LeftButton and self.dragging:
			self.dragging = False

			# Ensure rectangle is large enough for the pet
			min_width = self.pet_rect.width() + 20
			min_height = self.pet_rect.height() + 20

			if self.selection_rect.width() < min_width or self.selection_rect.height() < min_height:
				center = self.selection_rect.center()
				self.selection_rect.setSize(QSize(max(min_width, self.selection_rect.width()),
											  max(min_height, self.selection_rect.height())))
				self.selection_rect.moveCenter(center)

			# Teleport pet inside if it's outside
			if not self.selection_rect.contains(self.pet_rect):
				new_x = max(self.selection_rect.left(),
						 min(self.selection_rect.right() - self.pet_rect.width(), self.selection_rect.center().x()))
				new_y = max(self.selection_rect.top(),
						 min(self.selection_rect.bottom() - self.pet_rect.height(), self.selection_rect.center().y()))
				# Trigger pet teleport via callback (or handle it externally)
				self.callback(self.selection_rect, QPoint(new_x, new_y))
			else:
				self.callback(self.selection_rect)
			self.close()


if __name__ == "__main__":
	app = QApplication([])
	pet = VirtualPet()
	pet.show()
	sys.exit(app.exec_())
