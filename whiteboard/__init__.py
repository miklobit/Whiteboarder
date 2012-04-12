from numpy import *
from numpy.linalg import *
from whiteboard.trig import Radian, Angle
import os, sys, pygame
from pygame.locals import *
import cairo
from datetime import datetime, timedelta
class Brush(object):
	def __init__(self, color, scale, aspect, rotation):
		self.color = color
		self.scale = scale
		self.aspect = aspect
		self.rotation = rotation

		width = aspect
		height = 1
		left = width/(-2.)
		top = height/(-2.)
		right = left+width
		bottom = top+height

		c = Camera()
		c.scale(scale)
		c.rotate(rotation)

		pp = c.points_in( (
			( left, top ), 
			( right, top ),
			( left, bottom ),
			( right, bottom )
		) )
		bbtop = min( ( p[1] for p in pp ) )
		bbbottom = max( ( p[1] for p in pp ) )
		bbleft = min( ( p[0] for p in pp ) )
		bbright = max( ( p[0] for p in pp ) )
		self.bbox = pygame.Rect( bbleft, bbtop, bbright - bbleft, bbbottom - bbtop )
		self.points = pp
		



class Camera(object):
	def __init__(self):
		self.matrix = array([
			[1., 0., 0.],
			[0., 1., 0.],
			[0., 0., 1.]
		])
		self.dirty_rectangles = []
	def move(self, delta):
		mm = array([
			[1., 0., delta[0]],
			[0., 1., delta[1]],
			[0., 0., 1. ]
		])
		self.matrix = dot(self.matrix, mm)
	def rotate(self, angle):
		if not isinstance(angle, Angle):
			angle = Radian(angle)
		mm = array([
			[ angle.cos(), -angle.sin(), 0. ],
			[ angle.sin(), angle.cos(),  0. ],
			[ 0.,          0.,           1. ]
		])
		self.matrix = dot(self.matrix, mm)
	def scale(self, x, y=None):
		if y is None: y = x
		mm = array([
			[ x, 0., 0. ],
			[ 0., y, 0. ],
			[ 0., 0., 1. ]
		])
		self.matrix = dot(self.matrix, mm)
	def point_in(self, point):
		pm = array([
			[point[0]],
			[point[1]],
			[1.]
		])
		pt = dot(self.matrix, pm)
		return pt[0][0], pt[1][0]
	def points_in(self, points):
		return [ self.point_in(pp) for pp in points ]
	def point_out(self, point):
		pm = array([
			[point[0]],
			[point[1]],
			[1.]
		])
		pt = dot(inv(self.matrix), pm)
		return pt[0][0], pt[1][0]
	def points_out(self, points):
		return [ self.point_out(pp) for pp in points ]
	def rect_in(self, rect):
		p = (
			( rect.left, rect.top ),
			( rect.left + rect.width, rect.top ),
			( rect.left + rect.width, rect.top + rect.height),
			( rect.left , rect.top + rect.height )
		)
		pm = self.points_in(p)
		
		bp = (
			min( ( p[0] for p in pm ) ),
			max( ( p[0] for p in pm ) ),
			min( ( p[1] for p in pm ) ),
			max( ( p[1] for p in pm ) ),
		)
		return pygame.Rect(
			bp[0],
			bp[2],
			bp[1]-bp[0],
			bp[3]-bp[2]
		)
	def rect_out(self, rect):
		p = (
			( rect.left, rect.top ),
			( rect.left + rect.width, rect.top ),
			( rect.left + rect.width, rect.top + rect.height),
			( rect.left , rect.top + rect.height )
		)
		pm = self.points_out(p)
		
		bp = (
			min( ( p[0] for p in pm ) ),
			max( ( p[0] for p in pm ) ),
			min( ( p[1] for p in pm ) ),
			max( ( p[1] for p in pm ) ),
		)
		return pygame.Rect(
			bp[0],
			bp[2],
			bp[1]-bp[0],
			bp[3]-bp[2]
		)
	def draw(self, brush, points):
		points = self.points_in(points)

		dist = lambda l, r : sqrt( (r[0]-l[0])*(r[0]-l[0]) + (r[1]-l[1])*(r[1]-l[1]) )
		slope = lambda l, r : ( r[1] - l[1] ) / (r[0] - l[0] )
		context = self.context
		context.new_path()

		if len(points) == 4:
			d = dist(points[1], points[2])

			s1 = slope(points[0], points[1])
			s2 = slope(points[2], points[3])

			if math.isnan(s1):
				a1 = Radian(0.)
			elif math.isinf(s1):
				a1 = Radian(math.pi/2.)
			else:
				a1 = Radian.arctan(s1)

			if math.isnan(s2):
				a2 = Radian(0.)
			elif math.isinf(s2):
				a2 = Radian(math.pi/2.)
			else:
				a2 = Radian.arctan(s2)

			
			cp1 = ( a1.cos()*d/2. + points[1][0], a1.sin()*d/2. + points[1][1] )
			cp2 = ( points[2][0] - a2.cos()*d/2., points[2][1] - a1.sin()*d/2. )
			context.move_to(*(points[1]))
			context.curve_to(*( coord for p in ( cp1, cp2, points[2] ) for coord in p ))

		scale = self.point_in( ( brush.scale*1.41, brush.scale*1.41 ) )

		context.set_source_rgb(*brush.color)
		context.stroke()


		# self.dirty_rectangles.append( pygame.draw.line(self.screen, brush.color, p1, p2, brush.scale).inflate(scale) )

			

class CameraKeyframe(Camera):
	def __init__(self, time, isstop=True):
		super(CameraKeyframe, self).__init__()
		self.time = time
		self.isstop = isstop

class StrokeEvent(object):
	def __init__(self, time, pos, pressure = 1.0):
		self.time = time
		self.pos = pos
		self.pressure = pressure

class Stroke(object):
	def __init__(self, time, brush):
		self.time = time
		self.start = datetime.now()
		self.events = []
		self.brush = brush
	def record_event(self, pos, pressure=1.0):
		self.events.append(StrokeEvent( datetime.now() - self.start, pos, pressure ) )
		return self.events[-1]

	def draw(self, camera):
		for i in range(len(self.events)):
			points = self.events[i:i+4]
			camera.draw(self.brush, [ p.pos for p in points ])

class SubBeat(object):
	def __init__(self, number):
		self.number = number
		self.strokes = []
		self.current_stroke = None
		self.started = datetime.now()
	def start_stroke(self, brush):
		time = datetime.now() - self.started
		if self.current_stroke is not None:
			self.strokes.append(self.current_stroke)
		self.current_stroke = Stroke(time, brush)
		return self.current_stroke
	def end_stroke(self):
		self.strokes.append(self.current_stroke)
		self.current_stroke = None

	def draw(self, camera):
		for s in self.strokes:
			if s is not None:
				s.draw(camera)
	def draw_current(self, camera):
		if self.current_stroke is not None:
			self.current_stroke.draw(camera)



class Beat(object):
	def __init__(self, name, number):
		self.name = name
		self.number = number
		self.subbeats = []
		self.current_subbeat = None
	def start_subbeat(self):
		if self.current_subbeat is None:
			self.current_subbeat = SubBeat(0)
		else:
			self.subbeats.append(self.current_subbeat)
			self.current_subbeat = SubBeat(self.current_subbeat.number + 1)
		return self.current_subbeat
	def end_subbeat(self):
		if self.current_subbeat is not None:
			self.current_subbeat.end_stroke()
			self.subbeats.append(self.current_subbeat)
			self.current_subbeat = None

	def draw(self, camera):
		for sb in self.subbeats:
			sb.draw(camera)
		if self.current_subbeat is not None:
			self.current_subbeat.draw(camera)
	def draw_current(self, camera):
		if self.current_subbeat is not None:
			self.current_subbeat.draw_current(camera)


class Scene(object):
	def __init__(self):
		self.beats = []
		self.camera = Camera()
		self.brush = Brush( (0, 0, 0), 10, 0.33, Radian(math.pi/4.) )
		self.current_beat = None
		self.cached_surface = None
		self.camera_moved = True
		pygame.init()

		ar = 16.0/9.0

		size = width, height = 1080, int(1080/ar)
		self.size = size
		self.width = width
		self.height = height

		screen = pygame.display.set_mode(size, 0, 32)
		self.screen = screen
		pixels = pygame.surfarray.pixels2d(screen)
		self.cairo_surface = cairo.ImageSurface.create_for_data(
			pixels.data, cairo.FORMAT_RGB24, width, height
		)


	def start_beat(self, name=None):
		if name is None:
			if self.current_beat is None:
				name = "Beat"
				number = 0
			else:
				name = self.current_beat.name
				number = self.current_beat.number + 1
		else:
			number = 0

		if self.current_beat is not None:
			self.beats.append(self.current_beat)
		self.current_beat = Beat(name, number)
		return self.current_beat

	def end_beat(self):
		if self.current_beat is not None:
			self.current_beat.end_subbeat()
			self.beats.append(self.current_beat)
			self.current_beat = None

	def draw(self):
		self.camera.screen = self.screen
		self.camera.context = cairo.Context(self.cairo_surface)
		self.camera.dirty_rectangles = []
		if self.camera_moved:
			self.camera.context.set_source_rgb(255, 255, 255)
			self.camera.context.rectangle(0, 0, self.width, self.height)
			self.camera.context.fill()
			for b in self.beats:
				b.draw(self.camera) 
			if self.current_beat is not None:
				self.current_beat.draw(self.camera)
				self.current_beat.draw_current(self.camera)
			pygame.display.update()
			self.camera_moved = False
		else:
			if self.current_beat is not None:
				self.current_beat.draw_current(self.camera)
			pygame.display.update()
			# pygame.display.update(self.camera.dirty_rectangles)
	def move_camera(self, delta):
		# self.camera.move(self.camera.point_in(delta))
		self.camera.move(delta)
		self.camera_moved = True
	def scale_camera(self, scalex, scaley=None):
		self.camera.scale(scalex, scaley)
		self.camera_moved = True
	def rotate_camera(self, angle):
		self.camera.rotate(angle)
		self.camera_moved = True
