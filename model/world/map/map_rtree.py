# Math
from math import pi, sin, cos
import random

# Model
from model.geometry.rectangle import Rectangle
from model.geometry.segment import Segment
from model.world.map.obstacle import Obstacle
from model.geometry.polygon import Polygon
from model.geometry.point import Point

# Serialization
import pickle
import json

import rtree


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

        # Current obstacle position
        self._obstacles = []
        self._obstacle_tree = rtree.index.Index()

        # Initial obstacle position
        self._initial_obstacles = []
        self._initial_obstacles_tree = rtree.index.Index()

        self.current_goal = None

    @property
    def goal(self):
        return self.current_goal

    @property
    def obstacles(self):
        return self._obstacles

    def add_obstacle(self, obstacle):
        # polygon = shapely.geometry.Polygon(polygon_coords)
        obstacle_id = len(self.obstacles)
        self.obstacles.append(obstacle)
        self._obstacle_tree.insert(obstacle_id, obstacle.polygon.bounds)

    def backup_obstacles(self):
        self._initial_obstacles = self._obstacles.copy()
        # self._initial_obstacles_tree = self._obstacle_tree.copy()

    def is_obstacle(self, node1, node2):
        # import shapely
        # line = shapely.geometry.LineString(line_coords)
        line = Segment(node1, node2)
        for obstacle_id in self._obstacle_tree.intersection(line.bounds):
            if self.obstacles[obstacle_id].polygon.intersects(line):
            #if line.intersects(self.obstacles[obstacle_id].polygon):
                return True
        return False

    def get_neighbors(self, node, step_size=1, decimal_places=1):
        if len(node) == 3:
            x, y, z = node
        elif len(node) == 2:
            x, y = node
        neighbors = [
            (round(x - step_size, decimal_places), round(y, decimal_places)),
            (round(x + step_size, decimal_places), round(y, decimal_places)),
            (round(x, decimal_places), round(y - step_size, decimal_places)),
            (round(x, decimal_places), round(y + step_size, decimal_places)),
            (round(x - step_size, decimal_places), round(y - step_size, decimal_places)),
            (round(x + step_size, decimal_places), round(y - step_size, decimal_places)),
            (round(x - step_size, decimal_places), round(y + step_size, decimal_places)),
            (round(x + step_size, decimal_places), round(y + step_size, decimal_places)),
        ]
        return neighbors

    def get_map(self, robots):

        # Generate the goal
        goal_dist_range = self.goal_max_dist - self.goal_min_dist
        dist = self.goal_min_dist + (random.random() * goal_dist_range)
        phi = -pi + (random.random() * 2 * pi)
        x = int(dist * sin(phi))  # Round x to an integer
        y = int(dist * cos(phi))  # Round y to an integer
        goal = Point(x, y)

        # Generate a proximity test geometry for the goal
        r = self.min_goal_clearance
        n = 6
        goal_test_geometry = []
        for i in range(n):
            goal_test_geometry.append(
                Point(x + r * cos(i * 2 * pi / n), y + r * sin(i * 2 * pi / n))
            )
        goal_test_geometry = Polygon(goal_test_geometry)

        # Generate a proximity test geometry for the starting point
        r = self.obs_min_dist
        n = 6
        start_test_geometry = []
        for i in range(n):
            start_test_geometry.append(
                Point(x + r * cos(i * 2 * pi / n), y + r * sin(i * 2 * pi / n))
            )
        start_test_geometry = Polygon(start_test_geometry)

        # Obstacles parameters range
        obs_width_range = self.obs_max_width - self.obs_min_width
        obs_height_range = self.obs_max_height - self.obs_min_height
        obs_dist_range = self.obs_max_dist - self.obs_min_dist

        # test_geometries contains the robots and the goal
        test_geometries = [r.body for r in robots] + [
            goal_test_geometry
        ] + [
                              start_test_geometry
                          ]

        # Generate moving obstacles
        obstacles = []
        num_moving_obstacles_generated = 0
        num_steady_obstacles_generated = 0
        while (num_moving_obstacles_generated < self.obs_moving_count or
               num_steady_obstacles_generated < self.obs_steady_count):

            # Generate dimensions
            width = self.obs_min_width + (random.random() * obs_width_range)
            height = self.obs_min_height + (random.random() * obs_height_range)

            # Generate position
            dist = self.obs_min_dist + (random.random() * obs_dist_range)
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

            # Check if the polygon intersects one of the test geometries
            intersects = False
            for test_geometry in test_geometries:
                intersects |= polygon.intersects(test_geometry)
                if intersects:
                    break

            # The polygon is good: add the velocity vector and create an obstacle
            if not intersects:

                # If we need to generate moving obstacles
                if num_moving_obstacles_generated < self.obs_moving_count:
                    vel = (
                        random.uniform(self.obs_min_lin_speed, self.obs_max_lin_speed),
                        random.uniform(self.obs_min_lin_speed, self.obs_max_lin_speed),
                        random.uniform(self.obs_min_ang_speed, self.obs_max_ang_speed)
                    )
                    num_moving_obstacles_generated += 1

                # If we are done with the generation of moving obstacles
                else:
                    vel = (0, 0, 0)
                    num_steady_obstacles_generated += 1

                obstacle = Obstacle(polygon, pose, vel)
                self.add_obstacle(obstacle)
        self.current_goal = goal

        # Backup the current map so that we can reset it later
        self.backup_obstacles()

    def reset_map(self):
        [self.add_obstacle(obstacle) for obstacle in self._initial_obstacles]

    def save_as_pickle(self, filename):
        with open(filename, "wb") as file:
            pickle.dump(self._initial_obstacles, file)
            pickle.dump(self.current_goal, file)

    def save_as_json(self, filename):
        data = {
            "initial_obstacles": [obstacle.to_dict() for obstacle in self._initial_obstacles],
            "current_goal": self.current_goal.to_dict()
        }

        with open(filename, "w") as file:
            json.dump(data, file)

    def save_map(self, filename):
        self.save_as_json(filename)

    def load_map_from_pickle(self, filename):
        with open(filename, "rb") as file:
            self._initial_obstacles = pickle.load(file)
            self._obstacles = [obstacle.copy() for obstacle in self._initial_obstacles]
            self.current_goal = pickle.load(file)

    def load_map_from_json_file(self, filename):
        with open(filename, 'rb') as file:
            data = json.load(file)
            self.load_map_from_json_data(data)

    def load_map_from_json_data(self, data):
        self.current_goal = Point.from_dict(data['current_goal'])

        # reset the current obstacle if present
        self._obstacles = []
        self._obstacle_tree = rtree.index.Index()

        obstacle_data = data['initial_obstacles']
        for obstacle_dictionary in obstacle_data:
            obstacle = Obstacle.from_dict(obstacle_dictionary)
            self.add_obstacle(obstacle)

        self.backup_obstacles()
        print('Map updated!')

    def load_map(self, filename):
        self.load_map_from_json_file(filename)