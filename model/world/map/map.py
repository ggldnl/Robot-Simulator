from abc import abstractmethod

# Math
from math import pi, sin, cos
import random

# Model
from model.geometry.rectangle import Rectangle
from model.world.map.obstacle import Obstacle
from model.geometry.point import Point
from model.geometry.circle import Circle
from model.geometry.pose import Pose
from model.geometry.intersection import check_intersection

# Serialization
import pickle
import json


class Map:

    def __init__(self,
                 # Obstacle parameters
                 obs_min_dist,
                 obs_max_dist,
                 obs_min_width,
                 obs_max_width,
                 obs_min_height,
                 obs_max_height,
                 obs_steady_count,
                 obs_moving_count,

                 # Speed
                 obs_min_lin_speed,
                 obs_max_lin_speed,
                 obs_min_ang_speed,
                 obs_max_ang_speed,

                 # Goal parameters
                 goal_min_dist,
                 goal_max_dist,

                 min_goal_clearance
                 ):

        # Set parameters

        # Distance from the center (spawning point)
        self.obs_min_dist = obs_min_dist
        self.obs_max_dist = obs_max_dist

        # Dimension of the obstacles
        self.obs_min_width = obs_min_width
        self.obs_max_width = obs_max_width
        self.obs_min_height = obs_min_height
        self.obs_max_height = obs_max_height

        # Number of steady obstacles
        self.obs_steady_count = obs_steady_count

        # Number of moving obstacles
        self.obs_moving_count = obs_moving_count

        # Obstacle speed
        self.obs_min_lin_speed = obs_min_lin_speed
        self.obs_max_lin_speed = obs_max_lin_speed
        self.obs_min_ang_speed = obs_min_ang_speed
        self.obs_max_ang_speed = obs_max_ang_speed

        # Goal distance from the spawning point
        self.goal_min_dist = goal_min_dist
        self.goal_max_dist = goal_max_dist

        self.min_goal_clearance = min_goal_clearance

        # Obstacles parameters range
        self.obs_width_range = self.obs_max_width - self.obs_min_width
        self.obs_height_range = self.obs_max_height - self.obs_min_height
        self.obs_dist_range = self.obs_max_dist - self.obs_min_dist

        # Initial obstacles
        self.initial_obstacles = None

        # Current obstacles
        self.obstacles = None

        self.current_goal = None

    @abstractmethod
    def _add_obstacle(self, obstacle):
        pass

    def _add_obstacles(self, obstacles):
        for obstacle in obstacles:
            self._add_obstacle(obstacle)

    def _generate_random_obstacle(self):

        # Generate dimensions
        width = self.obs_min_width + (random.random() * self.obs_width_range)
        height = self.obs_min_height + (random.random() * self.obs_height_range)

        # Generate position
        dist = self.obs_min_dist + (random.random() * self.obs_dist_range)
        phi = -pi + (random.random() * 2 * pi)
        x = dist * sin(phi)
        y = dist * cos(phi)

        # Generate orientation
        theta = random.random() * 360

        # We have a pose
        pose = (x, y, theta)

        # Create a polygon
        polygon = Rectangle(width, height)
        polygon.transform(pose)

        return polygon

    def generate(self, robots):

        # Generate the goal
        goal_dist_range = self.goal_max_dist - self.goal_min_dist
        dist = self.goal_min_dist + (random.random() * goal_dist_range)
        phi = -pi + (random.random() * 2 * pi)
        x = dist * sin(phi)
        y = dist * cos(phi)
        goal = Point(x, y)

        # Generate a proximity test geometry for the goal
        r = self.min_goal_clearance

        """
        n = 6
        goal_test_geometry = []
        for i in range(n):
            goal_test_geometry.append(
                Point(x + r * cos(i * 2 * pi / n), y + r * sin(i * 2 * pi / n))
            )
        goal_test_geometry = Polygon(goal_test_geometry)
        """
        goal_test_geometry = Circle(x, y, r)

        # Generate a proximity test geometry for the starting point
        r = self.obs_min_dist

        """
        n = 6
        start_test_geometry = []
        for i in range(n):
            start_test_geometry.append(
                Point(x + r * cos(i * 2 * pi / n), y + r * sin(i * 2 * pi / n))
            )
        start_test_geometry = Polygon(start_test_geometry)
        # start_test_geometry = Circle(Point(0, 0), r)
        """
        start_test_geometry = Circle(0, 0, r)

        # test_geometries contains the robots and the goal
        test_geometries = [r.outline for r in robots] + [goal_test_geometry, start_test_geometry]

        # Generate obstacles
        moving_obstacles = []
        while len(moving_obstacles) < self.obs_moving_count:

            polygon = self._generate_random_obstacle()

            # Check if the polygon intersects one of the test geometries
            intersects = False
            for test_geometry in test_geometries:
                intersects |= check_intersection(polygon, test_geometry)
                if intersects:
                    break

            # The polygon is good: add the velocity vector and create an obstacle
            if not intersects:

                obstacle = Obstacle(polygon)
                obstacle.set_random_velocity_vector()
                moving_obstacles.append(obstacle)

        steady_obstacles = []
        while len(steady_obstacles) < self.obs_steady_count:
            
            polygon = self._generate_random_obstacle()

            # Check if the polygon intersects one of the test geometries
            intersects = False
            for test_geometry in test_geometries:
                intersects |= check_intersection(polygon, test_geometry)
                if intersects:
                    break

            # The polygon is good: add the velocity vector and create an obstacle
            if not intersects:

                obstacle = Obstacle(polygon)
                steady_obstacles.append(obstacle)

        # Update the obstacles and the goal
        self._add_obstacles(moving_obstacles)
        self._add_obstacles(steady_obstacles)
        self.current_goal = goal

    @abstractmethod
    def reset_map(self):
        pass

    def load_map(self, filename):
        self.load_map_from_json_file(filename)

    def save_map(self, filename):
        self.save_as_json(filename)

    @abstractmethod
    def save_as_pickle(self, filename):
        pass

    @abstractmethod
    def save_as_json(self, filename):
        pass

    @abstractmethod
    def load_map_from_pickle(self, filename):
        pass

    def load_map_from_json_file(self, filename):
        with open(filename, 'rb') as file:
            data = json.load(file)
            self.load_map_from_json_data(data)

    @abstractmethod
    def load_map_from_json_data(self, data):
        pass
