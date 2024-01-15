import json

from model.exceptions.collision_exception import CollisionException
from model.world.map.map_builder import MapBuilder
from model.geometry.intersection import check_intersection
from model.geometry.circle import Circle
from model.world import view


class World:

    def __init__(self, dt):

        # Initialize world time
        self.world_time = 0.0  # seconds
        self.dt = dt  # seconds
        self.idx = 0

        # Initialize list of robots
        self.robots = []
        self.robots_initial_poses = []

        # Initialize list of controllers (one for each robot)
        self.controllers = []

        # Initialize the map
        self.world_map = None

    @property
    def map(self):
        if map is None:
            raise ValueError('Map has not yet been initialized!')
        return self.world_map

    def set_map(self, world_map):
        self.world_map = world_map

    def set_period(self, dt):
        self.dt = dt

    def add_robot(self, robot, controller):
        self.robots.append(robot)
        self.robots_initial_poses.append(robot.current_pose.copy())
        self.controllers.append(controller)

    def reset_robots(self):
        for robot, robot_initial_pose, controller in zip(self.robots, self.robots_initial_poses, self.controllers):
            controller.reset(robot_initial_pose)
            robot.reset(robot_initial_pose)

    def step(self):
        """
        Step the simulation through one time interval
        """

        dt = self.dt

        # Step all the obstacles
        self.world_map.step_motion(dt)

        for robot, controller in zip(self.robots, self.controllers):
            next_pose = controller.step()
            robot.target_pose = next_pose
            robot.step_motion(dt)

        # Apply physics interactions
        # self._apply_physics()

        # Increment world time
        self.world_time += dt

    def _apply_physics(self):
        self._detect_collisions()

    def _detect_collisions(self):
        """
        Test the world for existing collisions with solids.
        Raises a CollisionException if one occurs.
        """

        solids = self.world_map.obstacles + self.robots

        for robot in self.robots:

            polygon1 = robot.outline

            # Robots can collide with other robots and with the obstacles
            for solid in solids:

                if solid is not robot:  # Don't bother testing an object against itself

                    polygon2 = solid.polygon  # polygon2

                    # Don't bother testing objects that are not near each other
                    if polygon1.check_nearness(polygon2):
                        if check_intersection(polygon1, polygon2):
                            raise CollisionException(f'Robot {robot.name} collided with an obstacle.')

    # ---------------------------- JSON serialization ---------------------------- #

    def to_json(self, add_path=True, add_data_structures=True):
        """
        Serialize the world. We add a "view" field that contains shape dictionaries.
        There are three kinds of shape dictionaries (polygon, circle, segment). This
        is done to reduce code dependency between backend and frontend: the frontend
        only knows how to draw polygons, circles and segments. All the other data
        is not touched by the frontend and all the view data is not used from the
        backend when restoring a json.
        """

        # Store world information
        world_json = {
            "map": self.world_map.to_dict(),
            "robots": [
                {
                    # We will only need the pose for each robot since the robot itself can be
                    # dynamically changed (uploading a URDF)
                    "pose": robot.current_pose.to_dict()
                    
                } for robot in self.robots
            ],
            "controllers": [controller.search_algorithm.__class__.__name__ for controller in self.controllers],
            "dt": self.dt,
            "view": self.world_view(add_path=add_path, add_data_structures=add_data_structures)
        }

        return json.dumps(world_json)

    def world_view(self, add_path=True, add_data_structures=True):

        shapes = []

        # Add the obstacles
        for obstacle in self.world_map.obstacles:
            shapes.append(view.get_obstacle_view_dict(obstacle))

        # Add the robots
        for robot in self.robots:
            shapes.extend(view.get_robot_view_dict(robot))

        # Add the start and the goal points to the frame
        shapes.append(view.get_goal_view_dict(self.world_map.goal))

        # Add data structures
        if add_data_structures:
            for controller in self.controllers:
                shapes.extend(view.get_data_structures_view_dict(controller.search_algorithm.draw_list))

        # Add the path
        if add_path:
            for robot, controller in zip(self.robots, self.controllers):
                path = controller.search_algorithm.path
                if len(path) > 0:
                    shapes.extend(view.get_path_view_dict([robot.current_pose] + path))

        # return json.dumps(shapes_list)
        return shapes

    def from_json(self, json_data):
        """
        Reconstruct the world from the json_data. We completely discard the "view" field
        """

        # Restore the map starting from the view
        self.world_map.load_map_from_json_data(json_data["map"])

        # Load robots data
        robots_data = json_data["robots"]
        for robot, robot_data in zip(self.robots, robots_data):
            # TODO update the pose
            pass

        # Load the controllers
        controllers = json_data["controllers"]
        for current_controller, loaded_controller in zip(self.controllers, controllers):
            # TODO introduce from_dict and to_dict methods to each search algorithm to restore them;
            #   the from_dict should be a class method that returns an instance of a SearchAlgorithm
            pass

        # Load the dt
        self.dt = json_data["dt"]
